import flet as ft
import api_client


class MyOrdersScreen(ft.View):
    def __init__(self, page: ft.Page):
        self.page_ref = page
        self.orders_container = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

        super().__init__(
            route="/my-orders",
            appbar=ft.AppBar(
                title=ft.Text("سفارش‌های من"),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
                leading=ft.IconButton(
                    ft.Icons.ARROW_FORWARD,
                    on_click=lambda e: self.page_ref.navigate("/"),
                ),
            ),
            controls=[
                ft.Container(
                    content=self.orders_container,
                    padding=20,
                    expand=True,
                )
            ],
        )

    def load_orders(self):
        self.orders_container.controls.clear()

        try:
            orders = api_client.get_orders()
        except Exception as ex:
            self.orders_container.controls.append(
                ft.Text(f"خطا: {ex}", color=ft.Colors.RED)
            )
            self.page_ref.update()
            return

        if not orders:
            self.orders_container.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.RECEIPT_LONG, size=80, color=ft.Colors.GREY),
                            ft.Text("هنوز سفارشی ثبت نکرده‌اید.", size=16, color=ft.Colors.GREY),
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

        status_colors = {
            'pending': ft.Colors.ORANGE,
            'paid': ft.Colors.BLUE,
            'processing': ft.Colors.BLUE,
            'shipped': ft.Colors.GREEN,
            'delivered': ft.Colors.GREEN,
            'cancelled': ft.Colors.RED,
        }

        for order in orders:
            status = order.get("status", "pending")
            color = status_colors.get(status, ft.Colors.GREY)

            # --- دکمه‌ها و اطلاعات اضافی ---
            actions_row = ft.Row(spacing=10, wrap=True)

            # دکمه پرداخت (فقط برای pending)
            if status == "pending":
                async def pay_handler(e, on=order["order_number"]):
                    result = api_client.start_payment(on)
                    if result and result.get("payment_url"):
                        launcher = ft.UrlLauncher()
                        await launcher.launch_url(
                            result["payment_url"],
                            mode=ft.LaunchMode.EXTERNAL_APPLICATION,
                        )
                        self.page_ref.snack_bar = ft.SnackBar(
                            ft.Text("پرداخت را در مرورگر تکمیل کنید."),
                        )
                        self.page_ref.snack_bar.open = True
                        self.page_ref.update()
                    else:
                        self.page_ref.snack_bar = ft.SnackBar(
                            ft.Text("خطا در اتصال به درگاه پرداخت."),
                            bgcolor=ft.Colors.RED,
                        )
                        self.page_ref.snack_bar.open = True
                        self.page_ref.update()

                actions_row.controls.append(
                    ft.Button(
                        "💳 پرداخت",
                        icon=ft.Icons.PAYMENT,
                        width=130,
                        on_click=pay_handler,
                    )
                )

            # دکمه جزئیات (برای همه سفارش‌ها)
            def details_handler(e, on=order["order_number"]):
                detail = api_client.get_order_detail(on)
                if detail:
                    self.show_order_details_dialog(detail)

            actions_row.controls.append(
                ft.Button(
                    "📋 جزئیات",
                    icon=ft.Icons.INFO,
                    width=130,
                    on_click=details_handler,
                    bgcolor=ft.Colors.BLUE_GREY_400,
                    color=ft.Colors.WHITE,
                )
            )

            # دکمه حذف (فقط برای pending یا cancelled)
            if status in ["pending", "cancelled"]:
                def delete_handler(e, on=order["order_number"]):
                    def do_confirm(ev):
                        confirm_dialog.open = False
                        self.page_ref.update()
                        if api_client.delete_order(on):
                            self.page_ref.snack_bar = ft.SnackBar(
                                ft.Text("سفارش حذف شد."),
                                bgcolor=ft.Colors.GREEN,
                            )
                            self.page_ref.snack_bar.open = True
                            self.page_ref.update()
                            self.load_orders()

                    def do_cancel(ev):
                        confirm_dialog.open = False
                        self.page_ref.update()

                    confirm_dialog = ft.AlertDialog(
                        title=ft.Text("حذف سفارش"),
                        content=ft.Text(f"آیا از حذف سفارش {on} مطمئن هستید؟"),
                        actions=[
                            ft.TextButton("انصراف", on_click=do_cancel),
                            ft.Button("بله، حذف کن", bgcolor=ft.Colors.RED, color=ft.Colors.WHITE, on_click=do_confirm),
                        ],
                    )
                    self.page_ref.overlay.append(confirm_dialog)
                    confirm_dialog.open = True
                    self.page_ref.update()

                actions_row.controls.append(
                    ft.Button(
                        "🗑️ حذف",
                        icon=ft.Icons.DELETE,
                        width=130,
                        bgcolor=ft.Colors.RED,
                        color=ft.Colors.WHITE,
                        on_click=delete_handler,
                    )
                )

            # کد رهگیری (برای paid)
            if status == "paid":
                actions_row.controls.append(
                    ft.Text(
                        f"✅ کد رهگیری: {order.get('payment_ref_id', '—')}",
                        size=11,
                        color=ft.Colors.GREEN,
                        weight=ft.FontWeight.BOLD,
                    )
                )

            # --- ساخت کارت سفارش ---
            self.orders_container.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            order.get("order_number", ""),
                                            weight=ft.FontWeight.BOLD,
                                            size=14,
                                        ),
                                        ft.Container(
                                            content=ft.Text(
                                                order.get("status_display", status),
                                                size=11,
                                                color=ft.Colors.WHITE,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            bgcolor=color,
                                            border_radius=10,
                                            padding=5,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Text(f"فروشنده: {order.get('vendor_name', '')}", size=13),
                                ft.Text(
                                    f"مبلغ: {order.get('total', 0)} تومان",
                                    size=13,
                                    color=ft.Colors.RED,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    f"تاریخ: {order.get('created_at', '')[:10]}",
                                    size=11,
                                    color=ft.Colors.GREY,
                                ),
                                actions_row,
                            ],
                            spacing=8,
                        ),
                        padding=12,
                    )
                )
            )

        self.page_ref.update()

    def show_order_details_dialog(self, order):
        def close_dialog(e):
            dialog.open = False
            self.page_ref.update()

        items_column = ft.Column(spacing=8)
        for item in order.get("items", []):
            items_column.controls.append(
                ft.Row(
                    [
                        ft.Text(item.get("product_name", ""), size=13, expand=True),
                        ft.Text(f"{item.get('quantity', 1)} عدد", size=12, color=ft.Colors.GREY),
                        ft.Text(f"{item.get('total_price', 0)} تومان", size=13, color=ft.Colors.RED),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

        dialog = ft.AlertDialog(
            title=ft.Text(f"سفارش {order.get('order_number', '')}"),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"وضعیت: {order.get('status_display', '')}", size=13, weight=ft.FontWeight.BOLD),
                        ft.Text(f"فروشنده: {order.get('vendor_name', '')}", size=12),
                        ft.Text(f"گیرنده: {order.get('receiver_name', '')}", size=12),
                        ft.Text(f"تلفن: {order.get('receiver_phone', '')}", size=12),
                        ft.Text(
                            f"آدرس: {order.get('shipping_province', '')}، {order.get('shipping_city', '')}، {order.get('shipping_address', '')}",
                            size=12),
                        ft.Divider(),
                        ft.Text("محصولات:", size=13, weight=ft.FontWeight.BOLD),
                        items_column,
                        ft.Divider(),
                        ft.Text(f"جمع: {order.get('total', 0)} تومان", size=14, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.RED),
                    ],
                    spacing=5,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=400,
                height=400,
            ),
            actions=[ft.TextButton("بستن", on_click=close_dialog)],
        )
        self.page_ref.overlay.append(dialog)
        dialog.open = True
        self.page_ref.update()

