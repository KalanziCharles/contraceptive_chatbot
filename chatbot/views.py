from django.shortcuts import render
from django.http import JsonResponse
from .models import ChatHistory
import json
from .models import ChatHistory, ContraceptiveMethod
from .groq_ai import get_ai_response
from .models import HealthFacility
import math
from .nlp_model import predict_intent


# Homepage
def home(request):
    return render(request, "index.html")

#Chat UI
def chat_ui(request):
    return render(request, "chatbot/chat.html")

def calculate_distance(lat1, lon1, lat2, lon2):
    # Haversine formula (distance in KM)

    R = 6371  # Earth radius in km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

# ✅ Intent Detection
def detect_intents(message):

    intents = []
    message_lower = message.lower()
    words = message_lower.split()

    # AI intents
    if "side effect" in message_lower:
        intents.append("side_effect")

    if "recommend" in message_lower or "suitable" in message_lower:
        intents.append("recommendation")

    # Facility intents
    if "free" in words:
        intents.append("free_facility")

    if "private" in words:
        intents.append("private_facility")

    if "nearest" in words or "nearby" in words or "near" in words:
        intents.append("nearest_facility")
        intents.append("facility")

    if "facility" in words or "clinic" in words or "hospital" in words:
        intents.append("facility")

    # Default
    if not intents:
        intents.append("general")

    return intents

    message_lower = message.lower()

    if "facility" in message_lower or "clinic" in message_lower or "hospital" in message_lower:
        intent = "facility"

    if "free" in message_lower:
        intent = "free_facility"

    if "near" in message_lower or "nearest" in message_lower or "nearby" in message_lower:
        intent = "nearest_facility"

# 🔥 SMART DATA RETRIEVAL (FILTERED)
def get_contraceptive_data(user_message):

    methods = ContraceptiveMethod.objects.filter(
        name__icontains=user_message
    ) | ContraceptiveMethod.objects.filter(
        suitability__icontains=user_message
    ) | ContraceptiveMethod.objects.filter(
        description__icontains=user_message
    )

    # If nothing found → fallback to limited data
    if not methods.exists():
        methods = ContraceptiveMethod.objects.all()[:10]

    data = []
    for m in methods:
        data.append(
            f"""
Name: {m.name}
Description: {m.description}
Effectiveness: {m.effectiveness}
Advantages: {m.advantages}
Disadvantages: {m.disadvantages}
Side Effects: {m.side_effects}
Suitability: {m.suitability}
"""
        )

    return "\n".join(data)


# 🧠 CHAT MEMORY
def get_chat_history():
    chats = ChatHistory.objects.all().order_by('-id')[:5]

    history = ""
    for chat in reversed(chats):
        history += f"""
User: {chat.user_message}
Bot: {chat.bot_response}
"""
    return history

def chat_history(request):
    chats = ChatHistory.objects.all().order_by('-id')[:10]

    data = []
    for chat in chats:
        data.append({
            "user_message": chat.user_message,
            "bot_response": chat.bot_response
        })

    return JsonResponse({"history": data})

def is_contraceptive_related(message):

    keywords = [
        "contraceptive", "family planning", "birth control",
        "condom", "pill", "iud", "implant", "injection",
        "pregnancy prevention", "fertility", "reproductive",
        "side effects", "menstrual", "ovulation"
    ]

    message = message.lower()

    return any(keyword in message for keyword in keywords)

#Chatbot API
def chatbot_response(request):

    if request.method == "POST":
        response = "Sorry, I couldn't process your request."

        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            user_lat = data.get('latitude')
            user_lon = data.get('longitude')
            print("LAT:", user_lat, "LON:", user_lon)

            print("USER:", message)

            if not message:
                return JsonResponse({"response": "Please enter a message."})

            # 🔍 DETECT INTENTS FIRST
            intents = detect_intents(message)
            print("INTENTS:", intents)

            # ✅ ALLOW FACILITY QUESTIONS EVEN IF NOT CONTRACEPTIVE
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
                    user_message=message,
                    bot_response=response
                )

                return JsonResponse({"response": response})

            # ✅ START BUILDING RESPONSE
            response_parts = []

            # 🤖 AI RESPONSE (only when needed)
            if (
                any(i in intents for i in ["side_effect", "recommendation"])
                or "nearest_facility" in intents
                or "facility" in intents
                or intents == ["general"]
            ):
                context = get_contraceptive_data(message)
                history = get_chat_history()
                ai_response = get_ai_response(message, context, history)
                response_parts.append(ai_response)

            # 🏥 FACILITY RESPONSE
            facility_keywords = ["facility", "clinic", "hospital", "health"]

            # 🔹 NEAREST FACILITY
            if "nearest_facility" in intents:

              print("➡️ Entered nearest facility block")

            if not user_lat or not user_lon:
                response_parts.append(
                    "📍 Please allow location access so I can find the nearest facility."
                )

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

            # 🔹 FREE FACILITIES
            if "free_facility" in intents:
                facilities = HealthFacility.objects.filter(offers_free_services=True)
                text = "🏥 Free health facilities:\n\n"

                if facilities.exists():
                    for f in facilities:
                        text += f"{f.name} ({f.location})\n"
                else:
                    text += "No free facilities found."

                response_parts.append(text)

            # 🔹 PRIVATE FACILITIES
            if "private_facility" in intents:
                facilities = HealthFacility.objects.filter(facility_type="private")
                text = "🏥 Private clinics:\n\n"

                if facilities.exists():
                    for f in facilities:
                        text += f"{f.name} ({f.location})\n"
                else:
                    text += "No private clinics found."

                response_parts.append(text)

            # 🔹 GENERAL FACILITIES
            if "facility" in intents:
                facilities = HealthFacility.objects.all()[:5]
                text = "🏥 Available facilities:\n\n"

                for f in facilities:
                    text += f"{f.name} ({f.location}) - {f.services}\n"

                response_parts.append(text)

            # ✅ FINAL RESPONSE
            if response_parts:
                response = "\n\n".join(response_parts)
            else:
                # fallback safety
                context = get_contraceptive_data(message)
                history = get_chat_history()
                response = get_ai_response(message, context, history)

            print("FINAL RESPONSE:", response)

            # ✅ SAVE CHAT
            ChatHistory.objects.create(
                user_message=message,
                bot_response=response
            )

        except Exception as e:
            print("ERROR:", str(e))
            response = "Server error occurred"

        return JsonResponse({"response": response})

    return JsonResponse({"response": "Invalid request"}, status=400)