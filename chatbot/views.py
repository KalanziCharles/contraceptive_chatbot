from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
import json
import math
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.shortcuts import redirect
from .forms import SignUpForm
from django.views.decorators.http import require_POST

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
    return render(request, "index.html")


# =========================
# 💬 CHAT UI (ENSURE CSRF COOKIE)
# =========================
@ensure_csrf_cookie
def chat_ui(request):
    return render(request, "chatbot/chat.html")

##SignUp Views
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

            # optionally attach anonymous sessions to this user
            anonymous_session_id = request.session.get("guest_chat_session_id")
            if anonymous_session_id:
                ChatSession.objects.filter(
                    id=anonymous_session_id,
                    user__isnull=True
                ).update(user=user)

            return redirect("chat_ui")
    else:
        form = SignUpForm()

    return render(request, "chatbot/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("chat_ui")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())

            anonymous_session_id = request.session.get("guest_chat_session_id")
            if anonymous_session_id:
                ChatSession.objects.filter(
                    id=anonymous_session_id,
                    user__isnull=True
                ).update(user=form.get_user())

            return redirect("chat_ui")
    else:
        form = AuthenticationForm()

    return render(request, "chatbot/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("chat_ui")

# =========================
# 📂 GET ALL CHAT SESSIONS
# =========================
def get_sessions(request):
    sessions = ChatSession.objects.all().order_by('-id')
    data = []

    for session in sessions:
        first_chat = ChatHistory.objects.filter(session=session).order_by("id").first()

        if first_chat:
            title = first_chat.user_message[:40]
        else:
            title = "New Chat"

        data.append({
            "id": session.id,
            "title": title
        })

    print("SESSIONS DATA:", data)
    return JsonResponse({"sessions": data})

def new_session(request):
    #print("NEW SESSION VIEW HIT")
    session = ChatSession.objects.create()
    return JsonResponse({"session_id": session.id})

# =========================
# 📜 CHAT HISTORY PER SESSION
# =========================
def chat_history(request):
    session_id = request.GET.get("session_id")

    chats = ChatHistory.objects.filter(
        session_id=session_id
    ).order_by("created_at")

    data = []

    for chat in chats:
        data.append({
            "id": chat.id,
            "user_message": chat.user_message,
            "bot_response": chat.bot_response
        })

    return JsonResponse({"history": data})


# =========================
# 📏 DISTANCE CALCULATION
# =========================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
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
        "facility", "clinic", "hospital", "where", "location"
    ]):
        intents.append("facility")

    if any(word in message for word in [
        "near", "nearest", "nearby"
    ]):
        intents.append("nearest_facility")

    if "where" in message and (
        "contraceptive" in message or
        "family planning" in message or
        "reproductive" in message
    ):
        if "facility" not in intents:
            intents.append("facility")
        if "nearest_facility" not in intents:
            intents.append("nearest_facility")

    if "free" in message:
        intents.append("free_facility")

    if "private" in message:
        intents.append("private_facility")

    if not intents:
        intents.append("general")

    return intents


# =========================
# 📚 FILTERED DATA FOR AI
# =========================
def get_contraceptive_data(user_message):

    methods = ContraceptiveMethod.objects.filter(
        name__icontains=user_message
    ) | ContraceptiveMethod.objects.filter(
        suitability__icontains=user_message
    ) | ContraceptiveMethod.objects.filter(
        description__icontains=user_message
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
# 🧠 CHAT HISTORY (AI MEMORY)
# =========================
def get_chat_history(session):
    chats = ChatHistory.objects.filter(session=session).order_by('-id')[:5]

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
        "contraceptive", "family planning", "birth control",
        "condom", "pill", "iud", "implant", "injection",
        "pregnancy", "fertility", "reproductive",
        "side effects", "menstrual", "ovulation"
    ]

    message = message.lower()
    return any(k in message for k in keywords)


# =========================
# 🤖 MAIN CHAT API
# =========================
def chatbot_response(request):
    if request.method != "POST":
        return JsonResponse({"response": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)

        message = data.get("message", "").strip()
        user_lat = data.get("latitude")
        user_lon = data.get("longitude")
        session_id = data.get("session_id")

        #print("LAT:", user_lat, "LON:", user_lon)
        #print("USER:", message)

        if not message:
            return JsonResponse({"response": "Please enter a message."})

        # =========================
        # SESSION HANDLING
        # =========================
        if session_id:
            session = ChatSession.objects.get(id=session_id)
        else:
            if request.user.is_authenticated:
                session = ChatSession.objects.create(user=request.user)
            else:
                session = ChatSession.objects.create()
                request.session["guest_chat_session_id"] = session.id

        # =========================
        # INTENTS
        # =========================
        intents = detect_intents(message)
        #print("INTENTS:", intents)

        allowed_facility_intents = [
            "facility",
            "free_facility",
            "private_facility",
            "nearest_facility"
        ]

        if not is_contraceptive_related(message) and not any(i in intents for i in allowed_facility_intents):
            response = (
                "I am a reproductive health assistant. "
                "I only provide information about contraceptives and nearby health facilities."
            )

            ChatHistory.objects.create(
                session=session,
                user_message=message,
                bot_response=response
            )

            return JsonResponse({
                "response": response,
                "session_id": session.id
            })

        response_parts = []
        response = "\n\n".join(response_parts)
        facility_response_added = False

        # =========================
        # FACILITY QUERYSET
        # =========================
        facility_queryset = (
    HealthFacility.objects.filter(services__icontains="family planning") |
    HealthFacility.objects.filter(services__icontains="contraceptive") |
    HealthFacility.objects.filter(services__icontains="reproductive") |
    HealthFacility.objects.filter(services__icontains="women") |
    HealthFacility.objects.filter(services__icontains="maternal")
        ).distinct()

        if not facility_queryset.exists():
            facility_queryset = HealthFacility.objects.all()

        # =========================
        # FACILITY LOGIC
        # =========================

        # nearest
        if "nearest_facility" in intents:
            if not user_lat or not user_lon:
                response_parts.append(
                    "📍 Please allow location access so I can find the nearest facility for contraceptive information."
                )
            else:
                nearest = None
                min_distance = float("inf")

                for f in facility_queryset:
                    if f.latitude is None or f.longitude is None:
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
                        f"🏥 Nearest facility for contraceptive information:\n"
                        f"{nearest.name} ({nearest.location})\n"
                        f"Services: {nearest.services}\n"
                        f"Distance: {min_distance:.2f} km"
                    )
                    facility_response_added = True
                else:
                    response_parts.append("No nearby contraceptive-related facilities found.")

        # free
        if "free_facility" in intents:
            free_facilities = facility_queryset.filter(offers_free_services=True)

            if free_facilities.exists():
                text = "🏥 Free facilities for contraceptive information:\n\n"
                for f in free_facilities[:5]:
                    text += f"{f.name} ({f.location}) - {f.services}\n"
            else:
                text = "No free contraceptive-related facilities found."

            response_parts.append(text)
            facility_response_added = True

        # private
        if "private_facility" in intents:
            private_facilities = facility_queryset.filter(facility_type="private")

            if private_facilities.exists():
                text = "🏥 Private facilities for contraceptive information:\n\n"
                for f in private_facilities[:5]:
                    text += f"{f.name} ({f.location}) - {f.services}\n"
            else:
                text = "No private contraceptive-related facilities found."

            response_parts.append(text)
            facility_response_added = True

        # general facility lookup
        if "facility" in intents and not facility_response_added:
            facilities = list(facility_queryset[:10])

            if user_lat and user_lon:
                ranked = []

                for f in facilities:
                    if f.latitude is not None and f.longitude is not None:
                        distance = calculate_distance(
                            float(user_lat),
                            float(user_lon),
                            float(f.latitude),
                            float(f.longitude)
                        )
                        ranked.append((distance, f))
                    else:
                        ranked.append((999999, f))

                ranked.sort(key=lambda x: x[0])

                text = "🏥 Facilities where you can get contraceptive information:\n\n"
                for distance, f in ranked[:5]:
                    if distance == 999999:
                        text += f"{f.name} ({f.location}) - {f.services}\n"
                    else:
                        text += f"{f.name} ({f.location}) - {f.services} [{distance:.2f} km]\n"
            else:
                text = "🏥 Facilities where you can get contraceptive information:\n\n"
                for f in facilities[:5]:
                    text += f"{f.name} ({f.location}) - {f.services}\n"

            response_parts.append(text)
            facility_response_added = True

        # =========================
        # AI RESPONSE
        # only for advice/explanation questions
        # =========================
        if (
            "side_effect" in intents
            or "recommendation" in intents
            or intents == ["general"]
        ):
            context = get_contraceptive_data(message)
            history = get_chat_history(session)
            ai_response = get_ai_response(message, context, history)
            response_parts.append(ai_response)

        # If no response built, fallback to AI
        if not response_parts:
            context = get_contraceptive_data(message)
            history = get_chat_history(session)
            ai_response = get_ai_response(message, context, history)
            response_parts.append(ai_response)

        # =========================
        # FINAL RESPONSE
        # =========================
        response = "\n\n".join(response_parts)
        print("FINAL RESPONSE:", response)

        # SAVE CHAT
        ChatHistory.objects.create(
            session=session,
            user_message=message,
            bot_response=response
        )

        return JsonResponse({
            "response": response,
            "session_id": session.id
        })

    except Exception as e:
        print("ERROR:", str(e))
        return JsonResponse({"response": "Server error occurred"})
    
@require_POST
def delete_single_message(request):
    try:
        data = json.loads(request.body)
        message_id = data.get("message_id")

        if not message_id:
            return JsonResponse({
                "status": "error",
                "message": "Message ID is required"
            })

        ChatHistory.objects.filter(id=message_id).delete()

        return JsonResponse({
            "status": "success",
            "message": "Message removed from history successfully"
        })

    except Exception as e:
        print("DELETE MESSAGE ERROR:", str(e))
        return JsonResponse({
            "status": "error",
            "message": "Failed to delete message"
        })