from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
import json
import math

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



# =========================
# 📂 GET ALL CHAT SESSIONS
# =========================
def get_sessions(request):
    from django.http import JsonResponse
    from .models import ChatSession, ChatHistory

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
    print("NEW SESSION VIEW HIT")
    session = ChatSession.objects.create()
    return JsonResponse({"session_id": session.id})

# =========================
# 📜 CHAT HISTORY PER SESSION
# =========================
def chat_history(request):
    session_id = request.GET.get("session_id")

    chats = ChatHistory.objects.filter(session_id=session_id).order_by("id")

    data = []
    for chat in chats:
        data.append({
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
        "facility", "clinic", "hospital",
        "where", "location"
    ]):
        intents.append("facility")

    if any(word in message for word in [
        "near", "nearest", "nearby"
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

        print("LAT:", user_lat, "LON:", user_lon)
        print("USER:", message)

        if not message:
            return JsonResponse({"response": "Please enter a message."})

        # =========================
        # SESSION HANDLING
        # =========================
        if session_id:
            session = ChatSession.objects.get(id=session_id)
        else:
            session = ChatSession.objects.create()

        # =========================
        # INTENTS
        # =========================
        intents = detect_intents(message)
        print("INTENTS:", intents)

        ALLOWED_FACILITY_INTENTS = [
            "facility",
            "free_facility",
            "private_facility",
            "nearest_facility"
        ]

        if not is_contraceptive_related(message) and not any(i in intents for i in ALLOWED_FACILITY_INTENTS):
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

        # =========================
        # BUILD RESPONSE
        # =========================
        response_parts = []

        # 🤖 AI RESPONSE
        context = get_contraceptive_data(message)
        history = get_chat_history(session)
        ai_response = get_ai_response(message, context, history)
        response_parts.append(ai_response)

        # =========================
        # 🏥 FACILITY LOGIC
        # =========================
        if "nearest_facility" in intents:

            if not user_lat or not user_lon:
                response_parts.append("📍 Please allow location access.")
            else:
                facilities = HealthFacility.objects.all()
                nearest = None
                min_distance = float('inf')

                for f in facilities:
                    if not f.latitude or not f.longitude:
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
                        f"Distance: {min_distance:.2f} km"
                    )
                else:
                    response_parts.append("No nearby facilities found.")

        if "free_facility" in intents:
            facilities = HealthFacility.objects.filter(offers_free_services=True)

            text = "🏥 Free facilities:\n\n"
            for f in facilities:
                text += f"{f.name} ({f.location})\n"

            response_parts.append(text)

        if "private_facility" in intents:
            facilities = HealthFacility.objects.filter(facility_type="private")

            text = "🏥 Private facilities:\n\n"
            for f in facilities:
                text += f"{f.name} ({f.location})\n"

            response_parts.append(text)

        if "facility" in intents:
            facilities = HealthFacility.objects.all()[:5]

            text = "🏥 Available facilities:\n\n"
            for f in facilities:
                text += f"{f.name} ({f.location}) - {f.services}\n"

            response_parts.append(text)

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