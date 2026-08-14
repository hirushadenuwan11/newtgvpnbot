import os
import asyncio
import traceback
from datetime import datetime, timedelta
from html import escape
from urllib.parse import urlparse

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from database import (
    init_database,
    save_user,
    get_user,
    get_user_count,

    get_packages,
    get_package,
    add_package,
    update_package,
    set_package_status,

    create_order,
    get_order,
    get_pending_orders,
    get_user_orders,

    update_order_status,
    get_order_count,
    get_pending_count,
    get_total_sales,

    save_payment_proof,
    save_config,
    get_user_configs,

    get_referral_stats,
    create_referral_earning,
)

from panel import (
    ThreeXUI,
    apply_sni,
)


# =========================================================
# ENV
# =========================================================

load_dotenv()


def env(name, default=""):
    value = os.getenv(name, default)
    return str(value or "").strip()


BOT_TOKEN = env("BOT_TOKEN")

ADMIN_ID = int(
    env("ADMIN_ID", "0") or 0
)

PANEL_URL = env("PANEL_URL").rstrip("/")

PANEL_USERNAME = env("PANEL_USERNAME")

PANEL_PASSWORD = env("PANEL_PASSWORD")

PANEL_API_TOKEN = env("PANEL_API_TOKEN")

BANK_NAME = env(
    "BANK_NAME",
    "YOUR BANK"
)

ACCOUNT_NAME = env(
    "ACCOUNT_NAME",
    "V2RayX"
)

ACCOUNT_NUMBER = env(
    "ACCOUNT_NUMBER",
    "0000000000"
)

BRANCH = env(
    "BRANCH",
    "YOUR BRANCH"
)

SUPPORT_USERNAME = env(
    "SUPPORT_USERNAME",
    "@v2rayx1_bot"
)

REFERRAL_PERCENTAGE = int(
    env(
        "REFERRAL_PERCENTAGE",
        "5"
    ) or 5
)


# =========================================================
# 3X-UI
# =========================================================

xui = ThreeXUI(
    PANEL_URL,
    PANEL_USERNAME,
    PANEL_PASSWORD,
    PANEL_API_TOKEN,
)


# =========================================================
# HELPERS
# =========================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def gb_text(value):
    value = safe_float(value)

    if value <= 0:
        return "Unlimited"

    return f"{value:g} GB"


def admin_only(user_id):
    return safe_int(user_id) == ADMIN_ID


def url_host(url):
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def html_text(value):
    return escape(str(value or ""))


# =========================================================
# MAIN MENU
# =========================================================

def main_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🛒 Buy Config",
                callback_data="buy"
            ),
            InlineKeyboardButton(
                "📦 My Configs",
                callback_data="configs"
            ),
        ],

        [
            InlineKeyboardButton(
                "🧾 My Orders",
                callback_data="orders"
            ),
            InlineKeyboardButton(
                "💳 Payment",
                callback_data="payment"
            ),
        ],

        [
            InlineKeyboardButton(
                "🎁 Referrals",
                callback_data="referrals"
            ),
            InlineKeyboardButton(
                "👤 Account",
                callback_data="account"
            ),
        ],

        [
            InlineKeyboardButton(
                "🆘 Support",
                callback_data="support"
            ),
        ],
    ])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not user:
        return

    referral = None

    if context.args:
        referral = (
            context.args[0]
            .strip()
            .upper()
        )

    try:

        save_user(
            user.id,
            user.username,
            user.first_name,
            referral,
        )

    except Exception as e:

        print(
            "save_user:",
            e
        )

    if not update.message:
        return

    await update.message.reply_text(

        f"🟢 <b>V2RayX</b>\n\n"
        f"Welcome, {html_text(user.first_name)}! 👋\n\n"
        f"Choose an option:",

        parse_mode="HTML",

        reply_markup=main_menu(),
    )


# =========================================================
# ID
# =========================================================

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not user:
        return

    await update.message.reply_text(

        f"🆔 <b>Telegram ID</b>\n\n"
        f"<code>{user.id}</code>",

        parse_mode="HTML",
    )


# =========================================================
# ADMIN
# =========================================================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not user:
        return

    if not admin_only(user.id):

        await update.message.reply_text(
            "⛔ Admin only."
        )

        return

    await send_admin_dashboard(
        user.id,
        context,
    )


async def send_admin_dashboard(admin_id, context):

    try:
        users = get_user_count()
    except Exception:
        users = 0

    try:
        orders = get_order_count()
    except Exception:
        orders = 0

    try:
        pending = get_pending_count()
    except Exception:
        pending = 0

    try:
        sales = get_total_sales()
    except Exception:
        sales = 0

    text = (

        "👨‍💼 <b>V2RayX</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"👥 Users: <b>{users}</b>\n"
        f"🧾 Orders: <b>{orders}</b>\n"
        f"⏳ Pending: <b>{pending}</b>\n"
        f"💰 Sales: <b>Rs.{sales:.2f}</b>\n\n"

        "🔌 <b>3X-UI</b>\n"
        f"<code>{html_text(PANEL_URL)}</code>\n\n"

        "Select an option:"
    )

    keyboard = [

        [
            InlineKeyboardButton(
                "🧾 Pending Orders",
                callback_data="admin_pending",
            )
        ],

        [
            InlineKeyboardButton(
                "📦 Packages",
                callback_data="admin_packages",
            )
        ],

        [
            InlineKeyboardButton(
                "📡 Panel Inbounds",
                callback_data="panel_inbounds",
            )
        ],

        [
            InlineKeyboardButton(
                "🔌 Test Panel",
                callback_data="panel_test",
            )
        ],

        [
            InlineKeyboardButton(
                "🔄 Refresh",
                callback_data="admin_home",
            )
        ],
    ]

    await context.bot.send_message(

        chat_id=admin_id,

        text=text,

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# =========================================================
# PACKAGES
# =========================================================

async def show_packages(query):

    try:

        packages = get_packages(True)

    except Exception as e:

        await query.edit_message_text(

            f"❌ <b>Package loading error.</b>\n\n"
            f"<code>{html_text(str(e)[:1500])}</code>",

            parse_mode="HTML",
        )

        return

    if not packages:

        await query.edit_message_text(

            "❌ No active packages.",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="back",
                    )
                ]

            ]),
        )

        return

    keyboard = []

    for row in packages:

        if len(row) < 8:
            continue

        (
            package_id,
            name,
            duration,
            price,
            active,
            inbound_id,
            traffic_gb,
            sni,
        ) = row[:8]

        keyboard.append([

            InlineKeyboardButton(

                f"📦 {name} | "
                f"{duration}D | "
                f"{gb_text(traffic_gb)} | "
                f"Rs.{safe_float(price):.0f}",

                callback_data=(
                    f"package_{package_id}"
                ),
            )
        ])

    keyboard.append([

        InlineKeyboardButton(
            "🔙 Back",
            callback_data="back",
        )

    ])

    await query.edit_message_text(

        "🛒 <b>V2RAY CONFIG STORE</b>\n\n"
        "Select your package:",

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# =========================================================
# EXTRACT LINKS
# =========================================================

def extract_links(data):

    result = []

    if data is None:
        return result

    if isinstance(data, str):

        text = data.strip()

        if text.startswith((
            "vless://",
            "vmess://",
            "trojan://",
            "ss://",
        )):

            result.append(text)

        return result

    if isinstance(data, (list, tuple)):

        for item in data:

            result.extend(
                extract_links(item)
            )

        return result

    if isinstance(data, dict):

        for key in (
            "value",
            "link",
            "url",
            "links",
            "externalLink",
            "externalLinks",
        ):

            if key in data:

                result.extend(
                    extract_links(
                        data[key]
                    )
                )

        return result

    return result


# =========================================================
# CREATE PANEL CONFIG
# =========================================================

async def create_panel_config(
    order_id,
    context,
):

    order = get_order(order_id)

    if not order:

        return False, "Order not found."

    # Expected database order:
    #
    # 0  order_id
    # 1  user_id
    # 2  package_id
    # 3  package_name
    # 4  duration
    # 5  price
    # 6  status
    # 7  inbound_id
    # 8  traffic_gb
    # 9  sni
    # 10 payment_proof
    # 11 config
    # 12 expiry
    # 13 created_at
    # 14 updated_at

    if len(order) < 15:

        return (
            False,
            "Database order format is invalid."
        )

    (
        db_order_id,
        user_id,
        package_id,
        package_name,
        duration,
        price,
        status,
        inbound_id,
        traffic_gb,
        sni,
        payment_proof,
        old_config,
        old_expiry,
        created_at,
        updated_at,
    ) = order[:15]

    user_id = safe_int(user_id)

    inbound_id = safe_int(inbound_id)

    duration = safe_int(duration)

    traffic_gb = safe_float(traffic_gb)

    # =====================================================
    # LOGIN
    # =====================================================

    try:

        ok, message = xui.login()

    except Exception as e:

        return (
            False,
            f"3X-UI login exception: {e}"
        )

    if not ok:

        return (
            False,
            f"3X-UI login failed: {message}"
        )

    # =====================================================
    # INBOUND
    # =====================================================

    try:

        inbound = xui.get_inbound(
            inbound_id
        )

    except Exception as e:

        return (
            False,
            f"Inbound error: {e}"
        )

    if not inbound:

        return (
            False,
            f"Inbound {inbound_id} not found."
        )

    # =====================================================
    # EXPIRY
    # =====================================================

    expiry_date = (
        datetime.now()
        + timedelta(days=duration)
    )

    expiry_ms = int(
        expiry_date.timestamp()
        * 1000
    )

    expiry_text = expiry_date.strftime(
        "%Y-%m-%d %H:%M"
    )

    # =====================================================
    # CLIENT EMAIL
    # =====================================================

    email = (
        f"vp_{user_id}_{order_id}"
        .replace("-", "_")
        .lower()
    )

    # =====================================================
    # CREATE CLIENT
    # =====================================================

    try:

        success, result = xui.create_client(

            inbound_id=inbound_id,

            email=email,

            expiry_ms=expiry_ms,

            traffic_gb=traffic_gb,

            telegram_id=user_id,
        )

    except Exception as e:

        return (
            False,
            f"Client creation error: {e}"
        )

    if not success:

        return (
            False,
            str(result)
        )

    await asyncio.sleep(1)

    # =====================================================
    # GET LINKS
    # =====================================================

    links = []

    try:

        link_ok, link_data = (
            xui.get_client_links(
                email
            )
        )

        if link_ok:

            links = extract_links(
                link_data
            )

    except Exception as e:

        print(
            "get_client_links:",
            e
        )

    # =====================================================
    # UUID
    # =====================================================

    client_uuid = None

    if isinstance(result, dict):

        client_uuid = (
            result.get("uuid")
            or result.get("id")
            or result.get("client_id")
        )

        client = result.get(
            "client"
        )

        if isinstance(client, dict):

            client_uuid = (
                client_uuid
                or client.get("id")
                or client.get("uuid")
            )

    # =====================================================
    # FALLBACK CLIENT
    # =====================================================

    if not client_uuid:

        try:

            client = (
                xui.get_client_from_inbound(
                    inbound,
                    email,
                )
            )

            if client:

                client_uuid = (
                    client.get("id")
                    or client.get("uuid")
                    or client.get("password")
                )

        except Exception as e:

            print(
                "Fallback client:",
                e
            )

    # =====================================================
    # FALLBACK VLESS
    # =====================================================

    if not links:

        protocol = str(
            inbound.get(
                "protocol",
                "",
            )
        ).lower()

        if (
            protocol == "vless"
            and client_uuid
        ):

            host = url_host(
                PANEL_URL
            )

            port = inbound.get(
                "port"
            )

            if host and port:

                stream = inbound.get(
                    "streamSettings",
                    {},
                )

                if not isinstance(
                    stream,
                    dict,
                ):

                    stream = {}

                network = stream.get(
                    "network",
                    "tcp",
                )

                security = stream.get(
                    "security",
                    "none",
                )

                config = (
                    f"vless://"
                    f"{client_uuid}@"
                    f"{host}:{port}"
                    f"?type={network}"
                    f"&security={security}"
                    f"#{package_name}"
                )

                links.append(
                    config
                )

    if not links:

        return (
            False,
            "Client created, but no usable "
            "configuration link was returned."
        )

    # =====================================================
    # SNI
    # =====================================================

    fixed_links = []

    for link in links:

        try:

            fixed_links.append(
                apply_sni(
                    link,
                    sni,
                )
            )

        except Exception as e:

            print(
                "SNI error:",
                e
            )

            fixed_links.append(
                link
            )

    config_text = "\n\n".join(
        fixed_links
    )

    # =====================================================
    # SAVE CONFIG
    # =====================================================

    try:

        save_config(
            order_id,
            config_text,
            expiry_text,
        )

        update_order_status(
            order_id,
            "COMPLETED",
        )

    except Exception as e:

        return (
            False,
            f"Database save error: {e}"
        )

    # =====================================================
    # REFERRAL
    # =====================================================

    try:

        create_referral_earning(
            user_id,
            order_id,
            REFERRAL_PERCENTAGE,
        )

    except Exception as e:

        print(
            "Referral:",
            e
        )

    # =====================================================
    # CUSTOMER CONFIG MESSAGE
    #
    # IMPORTANT:
    # <pre> makes the config monospace.
    # Telegram users can tap/copy it.
    # =====================================================

    try:

        safe_config = escape(
            config_text
        )

        customer_text = (

            "🎉 <b>YOUR CONFIG IS READY!</b>\n\n"

            f"🧾 Order: <code>{html_text(order_id)}</code>\n"
            f"📦 Package: <code>{html_text(package_name)}</code>\n"
            f"📊 Data: <code>{html_text(gb_text(traffic_gb))}</code>\n"
            f"🌐 SNI: <code>{html_text(sni)}</code>\n"
            f"📅 Expires: <code>{html_text(expiry_text)}</code>\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🔐 <b>CONFIG</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            f"<pre>{safe_config}</pre>\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "✅ Client created automatically.\n\n"
            "📋 Tap the config above to copy it."
        )

        await context.bot.send_message(

            chat_id=user_id,

            text=customer_text,

            parse_mode="HTML",
        )

    except Exception as e:

        print(
            "Customer config message:",
            e
        )

    return True, config_text


# =========================================================
# REFERRALS
# =========================================================

async def show_referrals(query):

    user = get_user(
        query.from_user.id
    )

    if not user:

        save_user(
            query.from_user.id,
            query.from_user.username,
            query.from_user.first_name,
        )

        user = get_user(
            query.from_user.id
        )

    try:

        total, paid, earned = (
            get_referral_stats(
                query.from_user.id
            )
        )

    except Exception:

        total = 0
        paid = 0
        earned = 0

    code = (
        user[3]
        if user
        else "N/A"
    )

    await query.edit_message_text(

        "🎁 <b>MY REFERRALS</b>\n\n"

        f"🔗 Code: <code>{html_text(code)}</code>\n\n"
        f"👥 Total: {total}\n"
        f"✅ Paid: {paid}\n"
        f"💰 Earned: Rs.{earned:.2f}\n\n"
        f"🎁 Reward: {REFERRAL_PERCENTAGE}%",

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "🏠 Home",
                    callback_data="back",
                )
            ]

        ]),
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    try:
        await query.answer()
    except Exception:
        pass

    user = query.from_user
    data = query.data or ""

    # =====================================================
    # ADMIN SECURITY
    # =====================================================

    admin_prefixes = (
        "admin_",
        "panel_",
        "approve_",
        "reject_",
        "pkg_",
        "editpkg_",
        "togglepkg_",
    )

    if data.startswith(admin_prefixes):

        if not admin_only(user.id):

            try:

                await query.answer(
                    "⛔ Admin only.",
                    show_alert=True,
                )

            except Exception:
                pass

            return

    # =====================================================
    # BUY
    # =====================================================

    if data == "buy":

        await show_packages(
            query
        )

        return

    # =====================================================
    # PACKAGE
    # =====================================================

    if data.startswith("package_"):

        try:

            package_id = int(
                data.split(
                    "_",
                    1
                )[1]
            )

        except Exception:

            await query.edit_message_text(
                "❌ Invalid package."
            )

            return

        try:

            package = get_package(
                package_id
            )

        except Exception as e:

            await query.edit_message_text(

                "❌ Package database error.\n\n"
                f"<code>{html_text(str(e)[:1000])}</code>",

                parse_mode="HTML",
            )

            return

        if not package:

            await query.edit_message_text(
                "❌ Package not found."
            )

            return

        if len(package) < 8:

            await query.edit_message_text(
                "❌ Package database format error."
            )

            return

        (
            pid,
            name,
            duration,
            price,
            active,
            inbound_id,
            traffic_gb,
            sni,
        ) = package[:8]

        if not active:

            await query.edit_message_text(
                "❌ Package disabled."
            )

            return

        try:

            order = create_order(
                user.id,
                package_id,
            )

        except Exception as e:

            await query.edit_message_text(

                "❌ <b>Order error.</b>\n\n"
                f"<code>{html_text(str(e)[:1200])}</code>",

                parse_mode="HTML",
            )

            return

        if not order:

            await query.edit_message_text(
                "❌ Could not create order."
            )

            return

        # Support dict result
        if isinstance(order, dict):

            order_id = order.get(
                "order_id"
            )

            order_package = order.get(
                "package_name",
                name,
            )

            order_duration = order.get(
                "duration",
                duration,
            )

            order_traffic = order.get(
                "traffic_gb",
                traffic_gb,
            )

            order_sni = order.get(
                "sni",
                sni,
            )

            order_price = safe_float(
                order.get(
                    "price",
                    price,
                )
            )

        else:

            # Fallback if create_order
            # returns only order id

            order_id = str(order)

            order_package = name
            order_duration = duration
            order_traffic = traffic_gb
            order_sni = sni
            order_price = safe_float(
                price
            )

        await query.edit_message_text(

            "🧾 <b>ORDER CREATED</b>\n\n"

            f"🆔 <code>{html_text(order_id)}</code>\n"
            f"📦 <code>{html_text(order_package)}</code>\n"
            f"⏱ <code>{order_duration} Days</code>\n"
            f"📊 <code>{html_text(gb_text(order_traffic))}</code>\n"
            f"🌐 SNI: <code>{html_text(order_sni)}</code>\n"
            f"💰 <b>Rs.{order_price:.2f}</b>\n\n"

            "Continue to payment:",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "💳 Continue Payment",
                        callback_data=(
                            f"pay_{order_id}"
                        ),
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="back",
                    )
                ],

            ]),
        )

        return

    # =====================================================
    # PAYMENT
    # =====================================================

    if data.startswith("pay_"):

        order_id = data[4:]

        order = get_order(
            order_id
        )

        if (
            not order
            or safe_int(order[1]) != user.id
        ):

            await query.edit_message_text(
                "❌ Invalid order."
            )

            return

        context.user_data[
            "payment_order"
        ] = order_id

        await query.edit_message_text(

            "💳 <b>PAYMENT INSTRUCTIONS</b>\n\n"

            f"🧾 Order: <code>{html_text(order_id)}</code>\n"
            f"📦 Package: <code>{html_text(order[3])}</code>\n"
            f"📊 Data: <code>{html_text(gb_text(order[8]))}</code>\n"
            f"💰 Amount: <code>Rs.{safe_float(order[5]):.2f}</code>\n\n"

            f"🏦 Bank: {html_text(BANK_NAME)}\n"
            f"👤 Account: {html_text(ACCOUNT_NAME)}\n"
            f"🔢 Number: <code>{html_text(ACCOUNT_NUMBER)}</code>\n"
            f"📍 Branch: {html_text(BRANCH)}\n\n"

            "After payment, upload the receipt.",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "📸 Upload Payment Slip",
                        callback_data=(
                            f"paid_{order_id}"
                        ),
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="back",
                    )
                ],

            ]),
        )

        return

    # =====================================================
    # PAYMENT UPLOAD
    # =====================================================

    if data.startswith("paid_"):

        order_id = data[5:]

        order = get_order(
            order_id
        )

        if (
            not order
            or safe_int(order[1]) != user.id
        ):

            await query.edit_message_text(
                "❌ Invalid order."
            )

            return

        context.user_data[
            "payment_order"
        ] = order_id

        await query.edit_message_text(

            "📸 <b>UPLOAD PAYMENT SLIP</b>\n\n"

            f"🧾 <code>{html_text(order_id)}</code>\n\n"

            "Send the receipt photo now.",

            parse_mode="HTML",
        )

        return

    # =====================================================
    # MY CONFIGS
    # =====================================================

    if data == "configs":

        configs = get_user_configs(
            user.id
        )

        if not configs:

            await query.edit_message_text(

                "📦 <b>MY CONFIGS</b>\n\n"
                "No configs yet.",

                parse_mode="HTML",

                reply_markup=InlineKeyboardMarkup([

                    [
                        InlineKeyboardButton(
                            "🛒 Buy",
                            callback_data="buy",
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            "🏠 Home",
                            callback_data="back",
                        )
                    ],

                ]),
            )

            return

        text = (
            "📦 <b>MY CONFIGS</b>\n\n"
        )

        for row in configs:

            if len(row) < 4:
                continue

            (
                order_id,
                config,
                created,
                expiry,
            ) = row[:4]

            text += (

                f"🧾 <code>{html_text(order_id)}</code>\n"
                f"📅 Expiry: <code>{html_text(expiry)}</code>\n\n"

                "<pre>"
                f"{escape(str(config))}"
                "</pre>\n\n"

                "━━━━━━━━━━━━━━━━━━\n\n"
            )

        await query.edit_message_text(

            text[:3900],

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="back",
                    )
                ],

            ]),
        )

        return

    # =====================================================
    # MY ORDERS
    # =====================================================

    if data == "orders":

        orders = get_user_orders(
            user.id
        )

        if not orders:

            await query.edit_message_text(

                "🧾 No orders yet.",

                reply_markup=InlineKeyboardMarkup([

                    [
                        InlineKeyboardButton(
                            "🛒 Buy",
                            callback_data="buy",
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            "🏠 Home",
                            callback_data="back",
                        )
                    ],

                ]),
            )

            return

        text = (
            "🧾 <b>MY ORDERS</b>\n\n"
        )

        for row in orders:

            if len(row) < 5:
                continue

            text += (

                f"🆔 <code>{html_text(row[0])}</code>\n"
                f"📦 {html_text(row[1])}\n"
                f"⏱ {row[2]} Days\n"
                f"💰 Rs.{safe_float(row[3]):.2f}\n"
                f"📌 {html_text(row[4])}\n\n"
            )

        await query.edit_message_text(

            text[:3900],

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="back",
                    )
                ],

            ]),
        )

        return

    # =====================================================
    # PAYMENT CENTER
    # =====================================================

    if data == "payment":

        await query.edit_message_text(

            "💳 <b>PAYMENT CENTER</b>\n\n"
            "Choose a package:",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🛒 Buy",
                        callback_data="buy",
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="back",
                    )
                ],

            ]),
        )

        return

    # =====================================================
    # REFERRALS
    # =====================================================

    if data == "referrals":

        await show_referrals(
            query
        )

        return

    # =====================================================
    # ACCOUNT
    # =====================================================

    if data == "account":

        account = get_user(
            user.id
        )

        code = (
            account[3]
            if account
            else "N/A"
        )

        await query.edit_message_text(

            "👤 <b>MY ACCOUNT</b>\n\n"

            f"Name: {html_text(user.first_name)}\n"
            f"Telegram ID: <code>{user.id}</code>\n"
            f"Username: @{html_text(user.username or 'None')}\n\n"
            f"🎁 Referral Code:\n"
            f"<code>{html_text(code)}</code>",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="back",
                    )
                ],

            ]),
        )

        return

    # =====================================================
    # SUPPORT
    # =====================================================

    if data == "support":

        await query.edit_message_text(

            "🆘 <b>SUPPORT</b>\n\n"
            f"Contact: @{html_text(SUPPORT_USERNAME)}",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="back",
                    )
                ],

            ]),
        )

        return

    # =====================================================
    # ADMIN HOME
    # =====================================================

    if data == "admin_home":

        await send_admin_dashboard(
            user.id,
            context
        )

        return

    # =====================================================
    # PANEL TEST
    # =====================================================

    if data == "panel_test":

        await query.edit_message_text(
            "🔌 Testing 3X-UI..."
        )

        try:

            ok, message = (
                xui.test_connection()
            )

        except Exception as e:

            ok = False
            message = str(e)

        if ok:

            text = (
                "✅ <b>3X-UI CONNECTED</b>\n\n"
                f"{html_text(message)}"
            )

        else:

            text = (
                "❌ <b>3X-UI CONNECTION FAILED</b>\n\n"
                f"<code>{html_text(str(message)[:1800])}</code>"
            )

        await query.edit_message_text(

            text,

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 Admin",
                        callback_data="admin_home",
                    )
                ],

            ]),
        )

        return

    # =====================================================
    # INBOUNDS
    # =====================================================

    if data == "panel_inbounds":

        await query.edit_message_text(
            "📡 Loading inbounds..."
        )

        try:

            inbounds = xui.list_inbounds()

            text = (
                "📡 <b>3X-UI INBOUNDS</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
            )

            if not inbounds:

                text += "No inbounds."

            else:

                for inbound in inbounds:

                    text += (

                        f"🆔 ID: "
                        f"<code>{inbound.get('id')}</code>\n"

                        f"📌 "
                        f"{html_text(inbound.get('remark'))}\n"

                        f"🔌 "
                        f"{html_text(inbound.get('protocol'))}\n"

                        f"🚪 Port: "
                        f"{html_text(inbound.get('port'))}\n\n"
                    )

        except Exception as e:

            text = (
                "❌ <b>INBOUND ERROR</b>\n\n"
                f"<code>{html_text(str(e)[:1800])}</code>"
            )

        await query.edit_message_text(

            text[:3900],

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔄 Refresh",
                        callback_data="panel_inbounds",
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 Admin",
                        callback_data="admin_home",
                    )
                ],

            ]),
        )

        return

    # =====================================================
    # ADMIN PACKAGES
    # =====================================================

    if data == "admin_packages":

        packages = get_packages(
            False
        )

        keyboard = []

        for row in packages:

            if len(row) < 8:
                continue

            (
                package_id,
                name,
                duration,
                price,
                active,
                inbound_id,
                traffic_gb,
                sni,
            ) = row[:8]

            icon = (
                "🟢"
                if active
                else "🔴"
            )

            keyboard.append([

                InlineKeyboardButton(

                    f"{icon} {name} | "
                    f"{gb_text(traffic_gb)} | "
                    f"IN:{inbound_id}",

                    callback_data=(
                        f"pkg_{package_id}"
                    ),
                )
            ])

        keyboard.append([

            InlineKeyboardButton(
                "➕ Add Package",
                callback_data="pkg_add",
            )

        ])

        keyboard.append([

            InlineKeyboardButton(
                "🔙 Admin",
                callback_data="admin_home",
            )

        ])

        await query.edit_message_text(

            "📦 <b>PACKAGE MANAGEMENT</b>\n\n"

            "Format:\n"
            "<code>Name | Days | Price | Inbound ID | GB | SNI</code>",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

        return

    # =====================================================
    # ADD PACKAGE
    # =====================================================

    if data == "pkg_add":

        context.user_data[
            "admin_action"
        ] = "add_package"

        await query.edit_message_text(

            "➕ <b>ADD PACKAGE</b>\n\n"

            "Send:\n\n"

            "<code>Name | Days | Price | Inbound ID | GB | SNI</code>\n\n"

            "Example:\n"

            "<code>"
            "Dialog Zoom | 30 | 1500 | 2 | 100 | zoom.example.com"
            "</code>\n\n"

            "Unlimited:\n"

            "<code>"
            "Dialog Unlimited | 30 | 1500 | 2 | 0 | zoom.example.com"
            "</code>",

            parse_mode="HTML",
        )

        return

    # =====================================================
    # PACKAGE DETAILS
    # =====================================================

    if data.startswith("pkg_"):

        try:

            package_id = int(
                data.split(
                    "_",
                    1
                )[1]
            )

        except Exception:

            return

        package = get_package(
            package_id
        )

        if not package:
            return

        if len(package) < 8:
            return

        (
            pid,
            name,
            duration,
            price,
            active,
            inbound_id,
            traffic_gb,
            sni,
        ) = package[:8]

        await query.edit_message_text(

            "📦 <b>PACKAGE DETAILS</b>\n\n"

            f"🆔 ID: <code>{pid}</code>\n"
            f"📦 Name: <code>{html_text(name)}</code>\n"
            f"⏱ Duration: <code>{duration} Days</code>\n"
            f"📊 Data: <code>{html_text(gb_text(traffic_gb))}</code>\n"
            f"💰 Price: <code>Rs.{safe_float(price):.2f}</code>\n"
            f"🔐 Inbound: <code>{inbound_id}</code>\n"
            f"🌐 SNI: <code>{html_text(sni)}</code>\n"
            f"📌 Status: "
            f"{'🟢 Active' if active else '🔴 Disabled'}",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "✏️ Edit",
                        callback_data=(
                            f"editpkg_{pid}"
                        ),
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔄 Toggle",
                        callback_data=(
                            f"togglepkg_{pid}"
                        ),
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 Packages",
                        callback_data="admin_packages",
                    )
                ],

            ]),
        )

        return

    # =====================================================
    # EDIT PACKAGE
    # =====================================================

    if data.startswith("editpkg_"):

        try:

            package_id = int(
                data.split(
                    "_",
                    1
                )[1]
            )

        except Exception:

            return

        package = get_package(
            package_id
        )

        if not package:
            return

        context.user_data[
            "admin_action"
        ] = "edit_package"

        context.user_data[
            "edit_package_id"
        ] = package_id

        await query.edit_message_text(

            "✏️ <b>EDIT PACKAGE</b>\n\n"

            "Send:\n"

            "<code>"
            "Name | Days | Price | Inbound ID | GB | SNI"
            "</code>\n\n"

            "Current:\n"

            f"<code>"
            f"{html_text(package[1])} | "
            f"{package[2]} | "
            f"{package[3]} | "
            f"{package[5]} | "
            f"{package[6]} | "
            f"{html_text(package[7])}"
            f"</code>",

            parse_mode="HTML",
        )

        return

    # =====================================================
    # TOGGLE PACKAGE
    # =====================================================

    if data.startswith("togglepkg_"):

        try:

            package_id = int(
                data.split(
                    "_",
                    1
                )[1]
            )

        except Exception:

            return

        package = get_package(
            package_id
        )

        if package:

            new_status = (
                0
                if package[4]
                else 1
            )

            set_package_status(
                package_id,
                new_status
            )

        await query.edit_message_text(

            "✅ Package status updated.",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 Packages",
                        callback_data="admin_packages",
                    )
                ],

            ]),
        )

        return

    # =====================================================
    # PENDING ORDERS
    #
    # IMPORTANT FIX:
    # We NEVER unpack blindly.
    # =====================================================

    if data == "admin_pending":

        try:

            orders = get_pending_orders()

        except Exception as e:

            await query.edit_message_text(

                "❌ <b>Pending error.</b>\n\n"
                f"<code>{html_text(str(e)[:1500])}</code>",

                parse_mode="HTML",
            )

            return

        if not orders:

            await query.edit_message_text(

                "🧾 <b>PENDING ORDERS</b>\n\n"
                "No pending orders.",

                parse_mode="HTML",

                reply_markup=InlineKeyboardMarkup([

                    [
                        InlineKeyboardButton(
                            "🔙 Admin",
                            callback_data="admin_home",
                        )
                    ]

                ]),
            )

            return

        keyboard = []

        for row in orders:

            # Your previous error:
            #
            # ValueError:
            # not enough values to unpack
            # expected 7, got 6
            #
            # Therefore we DON'T assume
            # exact number of returned columns.

            if len(row) < 6:

                print(
                    "Invalid pending order row:",
                    row
                )

                continue

            order_id = row[0]
            user_id = row[1]
            package_id = row[2]
            package_name = row[3]
            price = row[4]
            status = row[5]

            created_at = (
                row[6]
                if len(row) > 6
                else ""
            )

            keyboard.append([

                InlineKeyboardButton(

                    f"🧾 {order_id} | "
                    f"Rs.{safe_float(price):.0f} | "
                    f"{status}",

                    callback_data=(
                        f"admin_order_{order_id}"
                    ),
                )
            ])

        keyboard.append([

            InlineKeyboardButton(
                "🔙 Admin",
                callback_data="admin_home",
            )

        ])

        await query.edit_message_text(

            "🧾 <b>PENDING ORDERS</b>\n\n"
            "Select an order:",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

        return

    # =====================================================
    # ADMIN ORDER
    # =====================================================

    if data.startswith("admin_order_"):

        order_id = data.replace(
            "admin_order_",
            "",
            1
        )

        order = get_order(
            order_id
        )

        if not order:

            await query.edit_message_text(
                "❌ Order not found."
            )

            return

        if len(order) < 10:

            await query.edit_message_text(

                "❌ Order database format error.\n\n"
                "The database returned fewer columns "
                "than required.",

            )

            return

        await query.edit_message_text(

            "🧾 <b>ORDER DETAILS</b>\n\n"

            f"🆔 <code>{html_text(order[0])}</code>\n"
            f"👤 User: <code>{order[1]}</code>\n"
            f"📦 Package: <code>{html_text(order[3])}</code>\n"
            f"⏱ Duration: <code>{order[4]} Days</code>\n"
            f"📊 Data: <code>{html_text(gb_text(order[8]))}</code>\n"
            f"🌐 SNI: <code>{html_text(order[9])}</code>\n"
            f"💰 Price: <code>Rs.{safe_float(order[5]):.2f}</code>\n"
            f"🔐 Inbound: <code>{order[7]}</code>\n"
            f"📌 Status: <code>{html_text(order[6])}</code>",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "✅ Approve + Auto Config",
                        callback_data=(
                            f"approve_{order_id}"
                        ),
                    )
                ],

                [
                    InlineKeyboardButton(
                        "❌ Reject",
                        callback_data=(
                            f"reject_{order_id}"
                        ),
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 Pending",
                        callback_data="admin_pending",
                    )
                ],

            ]),
        )

        return

    # =====================================================
    # APPROVE
    # =====================================================

    if data.startswith("approve_"):

        order_id = data.replace(
            "approve_",
            "",
            1
        )

        order = get_order(
            order_id
        )

        if not order:

            await query.answer(
                "Order not found.",
                show_alert=True
            )

            return

        if order[6] == "COMPLETED":

            await query.answer(
                "Already completed.",
                show_alert=True
            )

            return

        if order[6] == "APPROVED":

            await query.answer(
                "Already processing.",
                show_alert=True
            )

            return

        update_order_status(
            order_id,
            "APPROVED"
        )

        await query.edit_message_text(

            "⏳ <b>Creating 3X-UI client...</b>\n\n"
            "Please wait.",

            parse_mode="HTML",
        )

        try:

            success, result = (
                await create_panel_config(
                    order_id,
                    context,
                )
            )

        except Exception as e:

            success = False
            result = str(e)

            traceback.print_exc()

        if success:

            await query.edit_message_text(

                "✅ <b>ORDER COMPLETED</b>\n\n"

                f"🧾 <code>{html_text(order_id)}</code>\n"
                f"📦 <code>{html_text(order[3])}</code>\n"
                f"📊 <code>{html_text(gb_text(order[8]))}</code>\n"
                f"🌐 <code>{html_text(order[9])}</code>\n"
                f"🔐 Inbound: <code>{order[7]}</code>\n\n"

                "🟢 Client created\n"
                "🟢 Traffic limit applied\n"
                "🟢 Expiry applied\n"
                "🟢 SNI applied\n"
                "🟢 Config sent",

                parse_mode="HTML",

                reply_markup=InlineKeyboardMarkup([

                    [
                        InlineKeyboardButton(
                            "🧾 Pending",
                            callback_data="admin_pending",
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            "🔙 Admin",
                            callback_data="admin_home",
                        )
                    ],

                ]),
            )

        else:

            update_order_status(
                order_id,
                "APPROVED"
            )

            await query.edit_message_text(

                "⚠️ <b>PAYMENT APPROVED</b>\n\n"

                f"🧾 <code>{html_text(order_id)}</code>\n\n"

                "❌ Auto config failed.\n\n"

                "Reason:\n"
                f"<code>{html_text(str(result)[:1800])}</code>",

                parse_mode="HTML",

                reply_markup=InlineKeyboardMarkup([

                    [
                        InlineKeyboardButton(
                            "🔁 Retry",
                            callback_data=(
                                f"approve_{order_id}"
                            ),
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            "🔙 Pending",
                            callback_data="admin_pending",
                        )
                    ],

                ]),
            )

        return

    # =====================================================
    # REJECT
    # =====================================================

    if data.startswith("reject_"):

        order_id = data.replace(
            "reject_",
            "",
            1
        )

        order = get_order(
            order_id
        )

        if order:

            update_order_status(
                order_id,
                "REJECTED"
            )

            try:

                await context.bot.send_message(

                    chat_id=order[1],

                    text=(

                        "❌ <b>PAYMENT REJECTED</b>\n\n"

                        f"🧾 <code>{html_text(order_id)}</code>\n\n"

                        "Please contact support."
                    ),

                    parse_mode="HTML",
                )

            except Exception:
                pass

        await query.edit_message_text(

            "❌ Order rejected.",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 Admin",
                        callback_data="admin_home",
                    )
                ]

            ]),
        )

        return

    # =====================================================
    # BACK
    # =====================================================

    if data == "back":

        await query.edit_message_text(

            "🟢 <b>V2RayX</b>\n\n"
            "Choose an option:",

            parse_mode="HTML",

            reply_markup=main_menu(),
        )

        return


# =========================================================
# PAYMENT PHOTO
# =========================================================

async def receive_payment_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user
    message = update.message

    if not user or not message:
        return

    order_id = context.user_data.get(
        "payment_order"
    )

    if not order_id:

        await message.reply_text(
            "❌ Select a payment order first."
        )

        return

    order = get_order(
        order_id
    )

    if (
        not order
        or safe_int(order[1]) != user.id
    ):

        await message.reply_text(
            "❌ Invalid order."
        )

        return

    if order[6] not in (
        "PENDING",
        "PAYMENT_SUBMITTED",
    ):

        await message.reply_text(
            "❌ This order cannot accept payment."
        )

        return

    try:

        photo = message.photo[-1]

        save_payment_proof(
            order_id,
            photo.file_id,
        )

        update_order_status(
            order_id,
            "PAYMENT_SUBMITTED",
        )

    except Exception as e:

        await message.reply_text(

            "❌ Payment slip save failed.\n\n"
            f"<code>{html_text(str(e)[:1000])}</code>",

            parse_mode="HTML",
        )

        return

    await message.reply_text(

        "✅ <b>PAYMENT SLIP RECEIVED!</b>\n\n"

        f"🧾 <code>{html_text(order_id)}</code>\n\n"

        "⏳ Waiting for admin approval.",

        parse_mode="HTML",
    )

    try:

        await context.bot.send_photo(

            chat_id=ADMIN_ID,

            photo=photo.file_id,

            caption=(

                "💳 <b>NEW PAYMENT</b>\n\n"

                f"🧾 <code>{html_text(order_id)}</code>\n"
                f"👤 {html_text(user.first_name)}\n"
                f"🆔 <code>{user.id}</code>\n"
                f"📦 <code>{html_text(order[3])}</code>\n"
                f"📊 <code>{html_text(gb_text(order[8]))}</code>\n"
                f"💰 Rs.{safe_float(order[5]):.2f}"
            ),

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "👁 View Order",
                        callback_data=(
                            f"admin_order_{order_id}"
                        ),
                    )
                ]

            ]),
        )

    except Exception as e:

        print(
            "Admin payment notification:",
            e
        )

    context.user_data.pop(
        "payment_order",
        None
    )


# =========================================================
# ADMIN TEXT
# =========================================================

async def receive_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user
    message = update.message

    if not user or not message:
        return

    if not admin_only(user.id):
        return

    action = context.user_data.get(
        "admin_action"
    )

    if not action:
        return

    text = (
        message.text or ""
    ).strip()

    # =====================================================
    # ADD PACKAGE
    # =====================================================

    if action == "add_package":

        try:

            parts = [
                x.strip()
                for x in text.split("|")
            ]

            if len(parts) != 6:

                raise ValueError(
                    "Need exactly 6 fields."
                )

            name = parts[0]
            duration = int(parts[1])
            price = float(parts[2])
            inbound_id = int(parts[3])
            traffic_gb = float(parts[4])
            sni = parts[5]

            if not name:
                raise ValueError(
                    "Package name is required."
                )

            if duration <= 0:
                raise ValueError(
                    "Invalid duration."
                )

            if price < 0:
                raise ValueError(
                    "Invalid price."
                )

            if inbound_id <= 0:
                raise ValueError(
                    "Invalid inbound ID."
                )

            if traffic_gb < 0:
                raise ValueError(
                    "Invalid GB."
                )

            if not sni:
                raise ValueError(
                    "SNI is required."
                )

            ok, msg = (
                xui.test_connection()
            )

            if not ok:

                raise ValueError(
                    msg
                )

            inbound = xui.get_inbound(
                inbound_id
            )

            if not inbound:

                raise ValueError(
                    "Inbound not found."
                )

            package_id = add_package(

                name,
                duration,
                price,
                inbound_id,
                traffic_gb,
                sni,
            )

            context.user_data.pop(
                "admin_action",
                None
            )

            await message.reply_text(

                "✅ <b>PACKAGE ADDED</b>\n\n"

                f"🆔 <code>{package_id}</code>\n"
                f"📦 <code>{html_text(name)}</code>\n"
                f"⏱ <code>{duration} Days</code>\n"
                f"📊 <code>{html_text(gb_text(traffic_gb))}</code>\n"
                f"💰 <code>Rs.{price:.2f}</code>\n"
                f"🔐 Inbound: <code>{inbound_id}</code>\n"
                f"🌐 SNI: <code>{html_text(sni)}</code>",

                parse_mode="HTML",
            )

        except Exception as e:

            await message.reply_text(

                "❌ <b>PACKAGE ADD FAILED</b>\n\n"

                f"<code>{html_text(str(e)[:1500])}</code>\n\n"

                "Format:\n"
                "<code>Name | Days | Price | Inbound ID | GB | SNI</code>",

                parse_mode="HTML",
            )

        return

    # =====================================================
    # EDIT PACKAGE
    # =====================================================

    if action == "edit_package":

        package_id = context.user_data.get(
            "edit_package_id"
        )

        try:

            if package_id is None:

                raise ValueError(
                    "Package ID missing."
                )

            parts = [
                x.strip()
                for x in text.split("|")
            ]

            if len(parts) != 6:

                raise ValueError(
                    "Need exactly 6 fields."
                )

            name = parts[0]
            duration = int(parts[1])
            price = float(parts[2])
            inbound_id = int(parts[3])
            traffic_gb = float(parts[4])
            sni = parts[5]

            if not name:
                raise ValueError(
                    "Package name is required."
                )

            if duration <= 0:
                raise ValueError(
                    "Invalid duration."
                )

            if price < 0:
                raise ValueError(
                    "Invalid price."
                )

            if inbound_id <= 0:
                raise ValueError(
                    "Invalid inbound ID."
                )

            if traffic_gb < 0:
                raise ValueError(
                    "Invalid GB."
                )

            if not sni:
                raise ValueError(
                    "SNI is required."
                )

            ok, msg = (
                xui.test_connection()
            )

            if not ok:

                raise ValueError(
                    msg
                )

            inbound = xui.get_inbound(
                inbound_id
            )

            if not inbound:

                raise ValueError(
                    "Inbound not found."
                )

            update_package(

                package_id,

                name,

                duration,

                price,

                inbound_id,

                traffic_gb,

                sni,
            )

            context.user_data.pop(
                "admin_action",
                None
            )

            context.user_data.pop(
                "edit_package_id",
                None
            )

            await message.reply_text(

                "✅ <b>PACKAGE UPDATED</b>\n\n"

                f"🆔 <code>{package_id}</code>\n"
                f"📦 <code>{html_text(name)}</code>\n"
                f"⏱ <code>{duration} Days</code>\n"
                f"📊 <code>{html_text(gb_text(traffic_gb))}</code>\n"
                f"💰 <code>Rs.{price:.2f}</code>\n"
                f"🔐 Inbound: <code>{inbound_id}</code>\n"
                f"🌐 SNI: <code>{html_text(sni)}</code>",

                parse_mode="HTML",
            )

        except Exception as e:

            await message.reply_text(

                "❌ <b>PACKAGE UPDATE FAILED</b>\n\n"
                f"<code>{html_text(str(e)[:1500])}</code>",

                parse_mode="HTML",
            )

        return


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):

    print()
    print("========== BOT ERROR ==========")

    try:

        traceback.print_exception(
            type(context.error),
            context.error,
            context.error.__traceback__,
        )

    except Exception:

        print(
            repr(context.error)
        )

    print(
        "==============================="
    )


# =========================================================
# VALIDATE SETTINGS
# =========================================================

def validate_settings():

    required = {

        "BOT_TOKEN": BOT_TOKEN,

        "ADMIN_ID": ADMIN_ID,

        "PANEL_URL": PANEL_URL,

        "PANEL_USERNAME": PANEL_USERNAME,

        "PANEL_PASSWORD": PANEL_PASSWORD,
    }

    missing = [

        key

        for key, value

        in required.items()

        if not value

    ]

    if missing:

        print(
            "Missing .env values:"
        )

        for item in missing:

            print(
                " -",
                item
            )

        return False

    return True


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print(
        "======================================"
    )
    print(
        " V2RayX"
    )
    print(
        "======================================"
    )

    if not validate_settings():

        input(
            "\nPress ENTER to close..."
        )

        return

    # =====================================================
    # DATABASE
    # =====================================================

    try:

        init_database()

        print(
            "Database: OK"
        )

    except Exception as e:

        print(
            "Database ERROR:",
            e
        )

        traceback.print_exc()

        input(
            "\nPress ENTER to close..."
        )

        return

    # =====================================================
    # PANEL
    # =====================================================

    print(
        "Panel:",
        PANEL_URL
    )

    try:

        ok, message = (
            xui.test_connection()
        )

        print(
            "3X-UI:",
            message
        )

        if not ok:

            print(
                "WARNING: Panel connection failed."
            )

    except Exception as e:

        print(
            "Panel test error:",
            e
        )

    # =====================================================
    # TELEGRAM
    # =====================================================

    try:

        app = (

            Application

            .builder()

            .token(
                BOT_TOKEN
            )

            .connect_timeout(
                30
            )

            .read_timeout(
                30
            )

            .write_timeout(
                30
            )

            .pool_timeout(
                30
            )

            .build()
        )

    except Exception as e:

        print(
            "Telegram application error:",
            e
        )

        traceback.print_exc()

        input(
            "\nPress ENTER to close..."
        )

        return

    # =====================================================
    # HANDLERS
    # =====================================================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "id",
            get_id
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_payment_photo
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            receive_text
        )
    )

    app.add_error_handler(
        error_handler
    )

    # =====================================================
    # STATUS
    # =====================================================

    print()
    print(
        "======================================"
    )
    print(
        " FEATURES"
    )
    print(
        "======================================"
    )
    print(
        "AUTO CLIENT       : ENABLED"
    )
    print(
        "GB LIMIT           : ENABLED"
    )
    print(
        "AUTO EXPIRY        : ENABLED"
    )
    print(
        "PACKAGE SNI        : ENABLED"
    )
    print(
        "PAYMENT SLIP       : ENABLED"
    )
    print(
        "ADMIN APPROVAL     : ENABLED"
    )
    print(
        "PACKAGE MANAGEMENT : ENABLED"
    )
    print(
        "MONOSPACE CONFIG   : ENABLED"
    )
    print(
        "======================================"
    )
    print()
    print(
        "BOT RUNNING..."
    )
    print()

    # =====================================================
    # RUN
    # =====================================================

    try:

        app.run_polling(
            drop_pending_updates=True
        )

    except KeyboardInterrupt:

        print(
            "\nBot stopped."
        )

    except Exception as e:

        print(
            "\nBOT STOPPED:"
        )

        print(
            str(e)
        )

        traceback.print_exc()

        input(
            "\nPress ENTER to close..."
        )


# =========================================================
# ENTRY
# =========================================================

if __name__ == "__main__":
    main()