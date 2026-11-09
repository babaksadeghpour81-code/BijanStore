import flet as ft


class SplashScreen(ft.View):
    def __init__(self, page: ft.Page, on_complete):
        self.page_ref = page
        self.on_complete = on_complete

        super().__init__(
            route="/splash",
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.SHOPPING_BAG,
                                size=100,
                                color=ft.Colors.WHITE,
                            ),
                            ft.Text(
                                "BijanStore",
                                size=36,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                            ),
                            ft.Text(
                                "فروشگاه آنلاین چندفروشندگی",
                                size=14,
                                color=ft.Colors.WHITE70,
                            ),
                            ft.ProgressRing(
                                width=30,
                                height=30,
                                color=ft.Colors.WHITE,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=20,
                    ),
                    alignment=ft.Alignment.CENTER,
                    expand=True,
                    bgcolor=ft.Colors.BLUE_700,
                )
            ],
        )

        # بعد از ۲ ثانیه، به صفحه اصلی برو
        import threading
        threading.Timer(2.0, lambda: self.page_ref.navigate("/")).start()

