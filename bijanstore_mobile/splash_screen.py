import flet as ft
import asyncio


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
                                color=ft.Colors.WHITE_70,
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

        # ✅ به جای threading.Timer از asyncio استفاده کن
        self.page_ref.run_task(self._navigate_after_delay)

    async def _navigate_after_delay(self):
        """بعد از ۲ ثانیه به صفحه اصلی برو"""
        await asyncio.sleep(2.0)
        await self.page_ref.push_route("/")