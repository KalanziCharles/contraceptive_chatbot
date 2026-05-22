from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

import json
import math

from .forms import SignUpForm

from .models import (
    ChatHistory,
    ContraceptiveMethod,
    HealthFacility,
    ChatSession
)

from .groq_ai import get_ai_response


# =========================
# 🏠 HOME
# =========================
def home(request):
    return render(request, "chatbot/chat.html")


# =========================
# 💬 CHAT UI
# =========================
@ensure_csrf_cookie
def chat_ui(request):
    return render(request, "chatbot/chat.html")


# =========================
# 🔐 SIGNUP
# =========================
def signup_view(request):

    if request.user.is_authenticated:
        return redirect("chat_ui")

    if request.method == "POST":

        form = SignUpForm(request.POST)

        if form.is_valid():

            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data.get("email", ""),
                password=form.cleaned_data["password"]
            )

            login(request, user)

            return redirect("chat_ui")

    else:
        form = SignUpForm()

    return render(
        request,
        "chatbot/signup.html",
        {"form": form}
    )


# =========================
# 🔐 LOGIN
# =========================
def login_view(request):

    if request.user.is_authenticated:
        return redirect("chat_ui")

    if request.method == "POST":

        form = AuthenticationForm(
            request,
            data=request.POST
        )

        if form.is_valid():

            login(request, form.get_user())

            return redirect("chat_ui")

    else:
        form = AuthenticationForm()

    return render(
        request,
        "chatbot/login.html",
        {"form": form}
    )


# =========================
# 🚪 LOGOUT
# =========================
def logout_view(request):
    logout(request)
    return redirect("chat_ui")


# =========================
# 📂 GET USER SESSIONS
# =========================
@login_required
def get_sessions(request):

    sessions = ChatSession.objects.filter(
        user=request.user
    ).order_by("-id")

    data = []

    for session in sessions:

        first_chat = ChatHistory.objects.filter(
            session=session
        ).order_by("id").first()

        title = (
            first_chat.user_message[:40]
            if first_chat
            else "New Chat"
        )

        data.append({
            "id": session.id,
            "title": title
        })

    return JsonResponse({
        "sessions": data
    })


# =========================
# ➕ CREATE NEW SESSION
# =========================
@login_required
def new_session(request):

    session = ChatSession.objects.create(
        user=request.user
    )

    return JsonResponse({
        "session_id": session.id
    })


# =========================
# 📜 CHAT HISTORY
# =========================
@login_required
def chat_history(request):

    session_id = request.GET.get("session_id")

    try:
        session = ChatSession.objects.get(
            id=session_id,
            user=request.user
        )

    except ChatSession.DoesNotExist:

        return JsonResponse({
            "history": []
        })

    chats = ChatHistory.objects.filter(
        session=session
    ).order_by("created_at")

    data = []

    for chat in chats:

        data.append({
            "id": chat.id,
            "user_message": chat.user_message,
            "bot_response": chat.bot_response
        })

    return JsonResponse({
        "history": data
    })


# =========================
# 📏 DISTANCE CALCULATION
# =========================
def calculate_distance(lat1, lon1, lat2, lon2):

    R = 6371

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return R * c


# =========================
# 🧠 INTENT DETECTION
# =========================
def detect_intents(message):

    intents = []

    message = message.lower()

    if "side effect" in message:
        intents.append("side_effect")

    if "recommend" in message or "best" in message:
        intents.append("recommendation")

    if any(word in message for word in [
        "facility",
        "clinic",
        "hospital",
        "where",
        "location"
    ]):
        intents.append("facility")

    if any(word in message for word in [
        "near",
        "nearest",
        "nearby"
    ]):
        intents.append("nearest_facility")

    if "free" in message:
        intents.append("free_facility")

    if "private" in message:
        intents.append("private_facility")

    if not intents:
        intents.append("general")

    return intents


# =========================
# 📚 CONTRACEPTIVE DATA
# =========================
def get_contraceptive_data(user_message):

    methods = (
        ContraceptiveMethod.objects.filter(
            name__icontains=user_message
        )
        |
        ContraceptiveMethod.objects.filter(
            suitability__icontains=user_message
        )
        |
        ContraceptiveMethod.objects.filter(
            description__icontains=user_message
        )
    )

    if not methods.exists():
        methods = ContraceptiveMethod.objects.all()[:10]

    data = []

    for m in methods:

        data.append(f"""
Name: {m.name}
Description: {m.description}
Effectiveness: {m.effectiveness}
Advantages: {m.advantages}
Disadvantages: {m.disadvantages}
Side Effects: {m.side_effects}
Suitability: {m.suitability}
""")

    return "\n".join(data)


# =========================
# 🧠 AI MEMORY
# =========================
def get_chat_history_memory(session):

    if not session or not session.user:
        return ""

    chats = ChatHistory.objects.filter(
        session=session
    ).order_by("-id")[:5]

    history = ""

    for chat in reversed(chats):

        history += f"""
User: {chat.user_message}
Bot: {chat.bot_response}
"""

    return history


# =========================
# 🔍 DOMAIN FILTER
# =========================
def is_contraceptive_related(message):

    keywords = [
        "contraceptive",
        "family planning",
        "birth control",
        "condom",
        "pill",
        "iud",
        "implant",
        "injection",
        "pregnancy",
        "fertility",
        "reproductive",
        "side effects",
        "menstrual",
        "ovulation"
    ]

    message = message.lower()

    return any(
        k in message
        for k in keywords
    )


# =========================
# 🤖 MAIN CHAT API
# =========================
def chatbot_response(request):

    if request.method != "POST":

        return JsonResponse({
            "response": "Invalid request"
        }, status=400)

    try:

        data = json.loads(request.body)

        message = data.get("message", "").strip()
        user_lat = data.get("latitude")
        user_lon = data.get("longitude")
        session_id = data.get("session_id")

        if not message:

            return JsonResponse({
                "response": "Please enter a message."
            })

        # =========================
        # SESSION HANDLING
        # =========================
        session = None

        if request.user.is_authenticated:

            if session_id:

                try:

                    session = ChatSession.objects.get(
                        id=session_id,
                        user=request.user
                    )

                except ChatSession.DoesNotExist:

                    session = ChatSession.objects.create(
                        user=request.user
                    )

            else:

                session = ChatSession.objects.create(
                    user=request.user
                )

        # =========================
        # INTENTS
        # =========================
        intents = detect_intents(message)

        allowed_facility_intents = [
            "facility",
            "free_facility",
            "private_facility",
            "nearest_facility"
        ]

        if (
            not is_contraceptive_related(message)
            and
            not any(
                i in intents
                for i in allowed_facility_intents
            )
        ):

            response = (
                "I am a reproductive health assistant. "
                "I only provide information about contraceptives "
                "and nearby health facilities."
            )

            if session:
                ChatHistory.objects.create(
                    session=session,
                    user_message=message,
                    bot_response=response
                )

            return JsonResponse({
                "response": response,
                "session_id": (
                    session.id if session else None
                )
            })

        response_parts = []
        facility_response_added = False

        # =========================
        # FACILITY QUERYSET
        # =========================
        facility_queryset = (
            HealthFacility.objects.filter(
                services__icontains="family planning"
            )
            |
            HealthFacility.objects.filter(
                services__icontains="contraceptive"
            )
            |
            HealthFacility.objects.filter(
                services__icontains="reproductive"
            )
            |
            HealthFacility.objects.filter(
                services__icontains="women"
            )
            |
            HealthFacility.objects.filter(
                services__icontains="maternal"
            )
        ).distinct()

        if not facility_queryset.exists():
            facility_queryset = HealthFacility.objects.all()

        # =========================
        # NEAREST FACILITY
        # =========================
        if "nearest_facility" in intents:

            if not user_lat or not user_lon:

                response_parts.append(
                    "📍 Please allow location access "
                    "so I can find nearby facilities."
                )

            else:

                nearest = None
                min_distance = float("inf")

                for f in facility_queryset:

                    if (
                        f.latitude is None
                        or
                        f.longitude is None
                    ):
                        continue

                    distance = calculate_distance(
                        float(user_lat),
                        float(user_lon),
                        float(f.latitude),
                        float(f.longitude)
                    )

                    if distance < min_distance:
                        min_distance = distance
                        nearest = f

                if nearest:

                    response_parts.append(
                        f"🏥 Nearest facility:\n"
                        f"{nearest.name} ({nearest.location})\n"
                        f"Services: {nearest.services}\n"
                        f"Distance: {min_distance:.2f} km"
                    )

                    facility_response_added = True

        # =========================
        # FREE FACILITIES
        # =========================
        if "free_facility" in intents:

            facilities = facility_queryset.filter(
                offers_free_services=True
            )

            text = (
                "🏥 Free contraceptive facilities:\n\n"
            )

            for f in facilities[:5]:

                text += (
                    f"{f.name} "
                    f"({f.location}) - "
                    f"{f.services}\n"
                )

            response_parts.append(text)

            facility_response_added = True

        # =========================
        # PRIVATE FACILITIES
        # =========================
        if "private_facility" in intents:

            facilities = facility_queryset.filter(
                facility_type="private"
            )

            text = (
                "🏥 Private contraceptive facilities:\n\n"
            )

            for f in facilities[:5]:

                text += (
                    f"{f.name} "
                    f"({f.location}) - "
                    f"{f.services}\n"
                )

            response_parts.append(text)

            facility_response_added = True

        # =========================
        # GENERAL FACILITY
        # =========================
        if (
            "facility" in intents
            and
            not facility_response_added
        ):

            text = (
                "🏥 Facilities for contraceptive services:\n\n"
            )

            for f in facility_queryset[:5]:

                text += (
                    f"{f.name} "
                    f"({f.location}) - "
                    f"{f.services}\n"
                )

            response_parts.append(text)

        # =========================
        # AI RESPONSE
        # =========================
        if (
            "side_effect" in intents
            or
            "recommendation" in intents
            or
            intents == ["general"]
        ):

            context = get_contraceptive_data(message)

            history = get_chat_history_memory(session)

            ai_response = get_ai_response(
                message,
                context,
                history
            )

            response_parts.append(ai_response)

        # fallback
        if not response_parts:

            context = get_contraceptive_data(message)

            history = get_chat_history_memory(session)

            ai_response = get_ai_response(
                message,
                context,
                history
            )

            response_parts.append(ai_response)

        # =========================
        # FINAL RESPONSE
        # =========================
        response = "\n\n".join(response_parts)

        # SAVE CHAT ONLY FOR LOGGED USERS
        if session:

            ChatHistory.objects.create(
                session=session,
                user_message=message,
                bot_response=response
            )

        return JsonResponse({
            "response": response,
            "session_id": (
                session.id if session else None
            )
        })

    except Exception as e:

        print("ERROR:", str(e))

        return JsonResponse({
            "response": "Server error occurred"
        })


# =========================
# 🗑 DELETE SINGLE MESSAGE
# =========================
@login_required
@require_POST
def delete_single_message(request):

    try:

        data = json.loads(request.body)

        message_id = data.get("message_id")

        if not message_id:

            return JsonResponse({
                "status": "error",
                "message": "Message ID required"
            })

        deleted, _ = ChatHistory.objects.filter(
            id=message_id,
            session__user=request.user
        ).delete()

        if not deleted:

            return JsonResponse({
                "status": "error",
                "message": "Message not found"
            })

        return JsonResponse({
            "status": "success",
            "message": "Message removed successfully"
        })

    except Exception as e:

        print("DELETE ERROR:", str(e))

        return JsonResponse({
            "status": "error",
            "message": "Failed to remove message"
        })