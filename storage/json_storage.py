"""Асинхронное JSON-хранилище состояний пользователей."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import aiofiles
import aiofiles.os

from models.user import UserState
from utils.logging import get_logger

logger = get_logger(__name__)


class JsonUserStorage:
    """Один JSON-файл на пользователя в папке users/."""

    def __init__(self, users_dir: Path) -> None:
        self._users_dir = users_dir
        self._locks: dict[int, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def ensure_ready(self) -> None:
        await aiofiles.os.makedirs(self._users_dir, exist_ok=True)

    def _path_for(self, user_id: int) -> Path:
        return self._users_dir / f"{user_id}.json"

    async def _get_lock(self, user_id: int) -> asyncio.Lock:
        async with self._global_lock:
            if user_id not in self._locks:
                self._locks[user_id] = asyncio.Lock()
            return self._locks[user_id]

    async def load(self, user_id: int) -> UserState:
        await self.ensure_ready()
        path = self._path_for(user_id)
        lock = await self._get_lock(user_id)

        async with lock:
            if not path.exists():
                state = UserState.create_default(user_id)
                await self._write_unlocked(path, state)
                logger.info("Created user state file for %s", user_id)
                return state

            try:
                async with aiofiles.open(path, "r", encoding="utf-8") as file:
                    raw = await file.read()
                data = json.loads(raw)
                return UserState.from_dict(data)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                logger.exception("Broken user JSON for %s: %s", user_id, exc)
                backup = path.with_suffix(".json.bak")
                try:
                    path.replace(backup)
                except OSError:
                    pass
                state = UserState.create_default(user_id)
                await self._write_unlocked(path, state)
                return state

    async def save(self, state: UserState) -> None:
        await self.ensure_ready()
        path = self._path_for(state.user_id)
        lock = await self._get_lock(state.user_id)
        async with lock:
            await self._write_unlocked(path, state)

    async def _write_unlocked(self, path: Path, state: UserState) -> None:
        payload = json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
        tmp_path = path.with_suffix(".json.tmp")
        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as file:
            await file.write(payload)
        await aiofiles.os.replace(tmp_path, path)
