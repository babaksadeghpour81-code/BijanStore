import flet as ft
from .. import api_client


class CartScreen(ft.View):
    def __init__(self, page: ft.Page, on_checkout):
        self.page_ref = page
        self.on_checkout = on_checkout
        self.cart_data = None
        self.items_container = ft.Column(spacing=10)
        self.total_text = ft.Text("", size=18, weight=ft.FontWeight.BOLD)

        super().__init__(
            route="/cart",
            appbar=ft.AppBar(
                title=ft.Text("سبد خرید"),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
                leading=ft.IconButton(
                    ft.Icons.ARROW_FORWARD,
                    on_click=lambda e: self.page_ref.go("/"),
                ),
            ),
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            self.items_container,
                            ft.Divider(),
                            ft.Row(
                                [ft.Text("جمع کل:", size=16), self.total_text],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Button(
                                "ادامه و ثبت سفارش",
                                width=300,
                                on_click=lambda e: self.on_checkout(),
                            ),
                        ],
                        spacing=15,
                    ),
                    padding=20,
                    expand=True,
                )
            ],
        )

    def load_cart(self):
        self.cart_data = api_client.get_cart()
        self.items_container.controls.clear()

        if not self.cart_data or not self.cart_data.get("items"):
            self.items_container.controls.append(
                ft.Text("سبد خرید شما خالی است.", color=ft.Colors.GREY)
            )
            self.total_text.value = "0 تومان"
            return

        for item in self.cart_data["items"]:
            product = item["product"]
            self.items_container.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(product["name"], weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{product['price']} تومان", color=ft.Colors.RED),
                                    ],
                                    expand=True,
                                ),
                                ft.IconButton(
                                    ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                    on_click=lambda e, i=item: self.change_qty(i["id"], i["quantity"] - 1),
                                ),
                                ft.Text(str(item["quantity"])),
                                ft.IconButton(
                                    ft.Icons.ADD_CIRCLE_OUTLINE,
                                    on_click=lambda e, i=item: self.change_qty(i["id"], i["quantity"] + 1),
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE,
                                    icon_color=ft.Colors.RED,
                                    on_click=lambda e, i=item: self.remove_item(i["id"]),
                                ),
                            ],
                        ),
                        padding=10,
                    )
                )
            )

        self.total_text.value = f"{self.cart_data['total_price']} تومان"

    def change_qty(self, item_id, new_qty):
        api_client.update_cart_item(item_id, new_qty)
        self.load_cart()
        self.page_ref.update()

    def remove_item(self, item_id):
        api_client.remove_from_cart(item_id)
        self.load_cart()
        self.page_ref.update()