import flet as ft
import api_client


class NotificationsScreen(ft.View):
    def __init__(self, page: ft.Page):
        self.page_ref = page
        self.notifications_container = ft.Column(spacing=10)

        super().__init__(
            route="/notifications",
            appbar=ft.AppBar(
                title=ft.Text("اعلان‌ها"),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
                leading=ft.IconButton(
                    ft.Icons.ARROW_FORWARD,
                    on_click=lambda e: self.page_ref.navigate("/"),
                ),
            ),
            controls=[
                ft.Container(
                    content=self.notifications_container,
                    padding=20,
                    expand=True,
                )
            ],
        )

    def load_notifications(self):
        self.notifications_container.controls.clear()

        try:
            notifications = api_client.get_notifications()
        except Exception as ex:
            self.notifications_container.controls.append(
                ft.Text(f"خطا: {ex}", color=ft.Colors.RED)
            )
            return

        if not notifications:
            self.notifications_container.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.NOTIFICATIONS_NONE, size=80, color=ft.Colors.GREY),
                            ft.Text("هیچ اعلانی ندارید.", size=16, color=ft.Colors.GREY),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=15,
                    ),
                    alignment=ft.Alignment.CENTER,
                    expand=True,
                    height=400,
                )
            )
            self.page_ref.update()
            return

        type_icons = {
            'order_status': ft.Icons.LOCAL_SHIPPING,
            'payment': ft.Icons.PAYMENT,
            'coupon': ft.Icons.LOCAL_OFFER,
            'vendor': ft.Icons.STORE,
            'settlement': ft.Icons.ACCOUNT_BALANCE_WALLET,
            'system': ft.Icons.NOTIFICATIONS,
        }

        for n in notifications:
            icon = type_icons.get(n.get("type"), ft.Icons.NOTIFICATIONS)
            is_read = n.get("is_read", False)

            def mark_read_handler(e, nid=n["id"]):
                if api_client.mark_notification_read(nid):
                    self.load_notifications()

            self.notifications_container.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    icon,
                                    size=32,
                                    color=ft.Colors.BLUE if not is_read else ft.Colors.GREY,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            n.get("title", ""),
                                            weight=ft.FontWeight.BOLD if not is_read else ft.FontWeight.NORMAL,
                                            size=14,
                                        ),
                                        ft.Text(n.get("message", ""), size=12, color=ft.Colors.GREY),
                                        ft.Text(
                                            n.get("created_at", "")[:16].replace("T", " "),
                                            size=10,
                                            color=ft.Colors.GREY,
                                        ),
                                    ],
                                    expand=True,
                                    spacing=3,
                                ),
                                ft.IconButton(
                                    ft.Icons.CHECK if not is_read else ft.Icons.CHECK_CIRCLE,
                                    icon_color=ft.Colors.GREEN if not is_read else ft.Colors.GREY,
                                    disabled=is_read,
                                    on_click=mark_read_handler,
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                        padding=12,
                        bgcolor=ft.Colors.BLUE_50 if not is_read else ft.Colors.WHITE,
                    )
                )
            )

        self.page_ref.update()

