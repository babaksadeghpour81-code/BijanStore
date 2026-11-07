from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'vendor', 'parent')
    list_filter = ('vendor',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}   # ← اضافه


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'category', 'price', 'stock', 'is_active')
    list_filter = ('is_active', 'vendor', 'category')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}