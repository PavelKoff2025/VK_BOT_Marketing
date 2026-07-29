from bot.handlers import menu, dialogs, report, audit, messages

# messages.labeler — последним: catch-all для обычного текста
labelers = [
    menu.labeler,
    dialogs.labeler,
    report.labeler,
    audit.labeler,
    messages.labeler,
]
