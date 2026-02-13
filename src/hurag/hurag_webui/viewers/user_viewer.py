from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..events import ClientEvents

from ..models import User
from ..services import login
from .. import logger
from nicegui import ui


def user_manager(ui_app, events: ClientEvents):
    current_user = User(**ui_app.storage.user.get("current_user", {}))

    with ui.dialog() as dialog, ui.card().classes("p-8 w-xl max-w-full gap-2"):
        ui.label("用户注册/登录").classes("text-h6 font-bold text-center w-full")
        ui.markdown(
            "请填写在 OA 系统登记的<u>**手机号**</u>以注册或登录。"
            "系统自动验证用户并获取姓名、组织机构等相关信息，无需用户填写。"
        ).classes("text-xs text-left text-zinc-500 w-full")
        account_inp = ui.input(
            label="用户账号:",
            placeholder="OA 登记的手机号码",
            value=current_user.account if current_user.id else "",
        ).classes("w-full")
        with ui.row().classes("w-full gap-4 mt-8 justify-end"):
            submit_btn = (
                ui.button("注册/登录", color="emerald-800")
                .props("flat")
                .classes("text-white px-6")
            )
            logout_btn = (
                ui.button("登出", color="zinc-200")
                .props("flat")
                .classes("text-gray-600 px-6")
            )

    # --- Callback functions ---
    async def submit(e):
        _ = e
        submitted_account = account_inp.value.strip()
        if not submitted_account or submitted_account.lower() == "guest":
            ui.notify("输入的用户账户无效", type="warning")
            return
        user = await login(submitted_account)
        if not user:
            ui.notify("账户未通过身份验证", type="negative")
        else:
            ui.notify(f"用户{user.username}({user.account})验证通过", type="positive")
            ui_app.storage.user["current_user"] = user.model_dump()
            ui_app.storage.client["current_user_account"] = user.account
            events.user_logged_in.emit(user.account)
            logger.info(f"User {user.username}({user.account}) logged in.")
            dialog.close()

    def logout(e):
        _ = e
        ui_app.storage.user["current_user"] = User().model_dump()
        ui_app.storage.client["current_user_account"] = None
        events.user_logged_in.emit(ui_app.storage.user["current_user"]["account"])
        dialog.close()

    # --- Binding properties and callbacks ---
    logout_btn.on_click(logout)
    submit_btn.on_click(submit)

    dialog.open()
