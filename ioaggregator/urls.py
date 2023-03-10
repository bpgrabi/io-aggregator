"""aggregator URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

import core.views
import user.views

urlpatterns = [
    path("", core.views.search, name="search"),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/signup", user.views.SignUpView.as_view(), name="signup"),
    path("email/<str:token>/", user.views.confirm_email, name="email_confirm"),
    path("search/", core.views.select_product, name="select_product"),
    path("multi-search/", core.views.multi_product, name="multi_product"),
    path("history/", core.views.shopping_history, name="shopping_history"),
    path("aggregate/", core.views.aggregate_cart, name="aggregate_cart"),
    path("add_product/", core.views.add_product, name="add_product"),
    path("shopping_cart/", core.views.shopping_cart, name="shopping_cart"),
    path("delete/", core.views.cart_delete, name="cart_delete"),
]
