# -*- coding: utf-8 -*-
from django.urls import path

from .views import FeedView

urlpatterns = [
    path("social/", FeedView.as_view(), name="feed"),
]
