import flet as ft
import api_client
from state import AppState
from login_screen import LoginScreen
from cart_screen import CartScreen
from checkout_screen import CheckoutScreen

def main(page: ft.Page):
    page.title = "BijanStore"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(font_family="Vazirmatn")

    # --- ۱. تعریف تابع ساخت صفحه اصلی ---
    def build_home_screen():
        # گرفتن تعداد سبد خرید
        api_client.get_cart()
        cart_count = 0
        if AppState.is_logged_in():
            try:
                cart_data = api_client.get_cart()
                if cart_data:
                    cart_count = cart_data.get("total_items", 0)
            except Exception:
                pass
        products_container = ft.Column(spacing=10)
        search_input = ft.TextField(
            hint_text="جستجوی محصول...",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=lambda e: load_products(e.control.value),
            expand=True,
            rtl=True,
        )

        def load_products(query=""):
            products_container.controls.clear()
            try:
                products = api_client.get_products(query)
            except Exception as ex:
                print(f"خطا در API: {ex}")
                products_container.controls.append(
                    ft.Text(f"خطا: {ex}", color=ft.Colors.RED)
                )
                page.update()
                return

            if not products:
                products_container.controls.append(
                    ft.Text("محصولی یافت نشد.", color=ft.Colors.GREY)
                )

            for p in products:
                products_container.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row(
                                [
                                    ft.Column(
                                        [
                                            ft.Text(p["name"], weight=ft.FontWeight.BOLD, size=15),
                                            ft.Text(f"{p['price']} تومان", color=ft.Colors.RED),
                                            ft.Text(
                                                f"فروشنده: {p['vendor']['name']}",
                                                size=11,
                                                color=ft.Colors.GREY,
                                            ),
                                        ],
                                        expand=True,
                                    ),
                                    ft.IconButton(
                                        ft.Icons.ADD_SHOPPING_CART,
                                        icon_color=ft.Colors.BLUE,
                                        on_click=lambda e, pid=p["id"]: add_product(pid),
                                    ),
                                ]
                            ),
                            padding=12,
                        )
                    )
                )
            page.update()

        def add_product(product_id):
            if not AppState.is_logged_in():
                page.navigate("/login")
                return
            api_client.add_to_cart(product_id, 1)
            page.snack_bar = ft.SnackBar(ft.Text("به سبد خرید اضافه شد"))
            page.snack_bar.open = True
            page.update()
            page.navigate("/")

        # بارگذاری اولیه
        load_products()

        return ft.View(
            route="/",
            appbar=ft.AppBar(
                title=ft.Text("BijanStore"),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
                actions=[
                    # سبد خرید
                    ft.IconButton(
                        ft.Icons.SHOPPING_CART,
                        on_click=lambda e: page.navigate("/cart"),
                    ),
                    # سفارش‌های من (فقط اگر لاگین باشه)
                    ft.IconButton(
                        ft.Icons.RECEIPT_LONG,
                        on_click=lambda e: page.navigate("/my-orders") if AppState.is_logged_in() else page.navigate(
                            "/login"),
                    ),
                    # اعلان‌ها (فقط اگر لاگین باشه)
                    ft.IconButton(
                        ft.Icons.NOTIFICATIONS,
                        on_click=lambda e: page.navigate(
                            "/notifications") if AppState.is_logged_in() else page.navigate("/login"),
                    ),
                    # کاربر
                    ft.IconButton(
                        ft.Icons.LOGIN if not AppState.is_logged_in() else ft.Icons.PERSON,
                        on_click=lambda e: page.navigate("/login") if not AppState.is_logged_in() else page.navigate(
                            "/profile"),
                    ),
                ],
            ),
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row([search_input]),
                            products_container,
                        ],
                        spacing=15,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    padding=20,
                    expand=True,
                )
            ],
        )

    # --- صفحه پروفایل ---
    def build_profile_screen():
        def do_logout(e):
            AppState.clear()
            page.navigate("/")
            page.update()

        return ft.View(
            route="/profile",
            appbar=ft.AppBar(
                title=ft.Text("پروفایل من"),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
                leading=ft.IconButton(
                    ft.Icons.ARROW_FORWARD,
                    on_click=lambda e: page.navigate("/"),
                ),
            ),
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.PERSON, size=80, color=ft.Colors.BLUE),
                            ft.Text(f"خوش آمدید، {AppState.username}", size=20, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            ft.Button(
                                "خروج از حساب",
                                icon=ft.Icons.LOGOUT,
                                color=ft.Colors.WHITE,
                                bgcolor=ft.Colors.RED,
                                on_click=do_logout,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=20,
                    ),
                    padding=40,
                    alignment=ft.Alignment.CENTER,
                    expand=True,
                )
            ],
        )

    def route_change(e=None):
        page.views.clear()
        route = page.route

        if route == "/login":
            page.views.append(
                LoginScreen(
                    page,
                    on_login_success=lambda: page.navigate("/"),
                )
            )
        elif route == "/cart":
            if not AppState.is_logged_in():
                page.navigate("/login")
                return
            cart_screen = CartScreen(
                page,
                on_checkout=lambda: page.navigate("/checkout"),
            )
            page.views.append(cart_screen)
            cart_screen.load_cart()
        elif route == "/profile":
            if not AppState.is_logged_in():
                page.navigate("/login")
                return
            page.views.append(build_profile_screen())
        elif route == "/checkout":
            if not AppState.is_logged_in():
                page.navigate("/login")
                return
            page.views.append(
                CheckoutScreen(
                    page,
                    on_success=lambda: page.navigate("/"),
                )
            )
        else:
            page.views.append(build_home_screen())

        page.update()

    # --- ۳. اتصال و شروع ---
    page.on_route_change = route_change
    route_change()  # فراخوانی مستقیم برای صفحه اول


ft.run(main)
