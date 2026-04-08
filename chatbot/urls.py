from django.urls import path
from . import views

urlpatterns = [
     path('', views.home, name='home'),
     path("chat-ui/", views.chat_ui, name="chat_ui"),
     path("chat/", views.chatbot_response, name="chatbot"),
     path("history/", views.chat_history, name="chat_history"),
]