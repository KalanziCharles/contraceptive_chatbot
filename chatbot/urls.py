from django.urls import path
from . import views

urlpatterns = [
    # Home page
    path('', views.home, name='home'),

    # Chat UI page (loads HTML frontend)
    path('chat-ui/', views.chat_ui, name='chat_ui'),

    # Chatbot API endpoint (POST from frontend)
    path('chat/', views.chatbot_response, name='chatbot'),

    # Chat history API (GET or POST depending on your view)
    path('history/', views.chat_history, name='chat_history'),

    path("sessions/", views.get_sessions),

    path("new-session/", views.new_session),
]