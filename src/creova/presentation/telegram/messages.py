START = (
    "Hi, I am <b>Creova</b>. I can help you turn a simple idea into a carefully "
    "designed AI image.\n\n"
    "Send me an idea or use /create to begin."
)

HELP = (
    "<b>Commands</b>\n"
    "/start - introduce Creova\n"
    "/create - start an assisted image request\n"
    "/status &lt;id&gt; - check generation status\n"
    "/history - view your recent images\n"
    "/cancel &lt;id&gt; - cancel a draft or request\n"
    "/whoami - show your identity and role\n"
    "/help - show this help\n\n"
    "Nano Banana and ChatGPT can help refine and generate images. Claude can help "
    "refine the creative brief, then Nano Banana or ChatGPT must generate the final image."
)

CREATE_STARTED = (
    "Which AI should help shape your image?\n\n"
    "Nano Banana and ChatGPT can refine and generate. Claude can refine the brief, "
    "then you will choose Nano Banana or ChatGPT to generate."
)

CREATE_PENDING_STORAGE = (
    "Which AI should help shape your image?\n\n"
    "The durable conversation store is not connected in this runtime."
)

STATUS_PENDING = "Status lookup will be available after confirmed requests are implemented."
HISTORY_PENDING = (
    "History will show your own retained image requests once generation is implemented."
)
CANCEL_PENDING = "Cancellation will be available for drafts and queued requests in the next phase."

PRIVATE_DENIED = "This bot is private and your account does not have access."
CALLBACK_DENIED = "You do not have access to Creova."
