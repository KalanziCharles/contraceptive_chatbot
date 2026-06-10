from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.http import HttpResponse

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


# =========================================
# 🏠 HOME
# =========================================
def home(request):
    return render(request, "chatbot/chat.html")


# =========================================
# 💬 CHAT UI
# =========================================
@ensure_csrf_cookie
def chat_ui(request):
    return render(request, "chatbot/chat.html")

def create_render_admin(request):
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser(
            username="admin",
            email="karaloscharlz@gmail.com",
            password="Admin123456"
        )
        return HttpResponse("Superuser created")
    return HttpResponse("Superuser already exists")


# =========================================
# 🔐 SIGNUP
# =========================================
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
    return render(request, "chatbot/signup.html", {"form": form})


# =========================================
# 🔐 LOGIN
# =========================================
def login_view(request):
    if request.user.is_authenticated:
        return redirect("chat_ui")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("chat_ui")
    else:
        form = AuthenticationForm()
    return render(request, "chatbot/login.html", {"form": form})


# =========================================
# 🚪 LOGOUT
# =========================================
def logout_view(request):
    logout(request)
    return redirect("chat_ui")


# =========================================
# 📂 GET SESSIONS
# =========================================
@login_required
def get_sessions(request):
    sessions = ChatSession.objects.filter(user=request.user).order_by("-updated_at", "-id")
    data = []
    for session in sessions:
        first_chat = ChatHistory.objects.filter(session=session).order_by("id").first()
        title = (first_chat.user_message[:40] if first_chat else "New Chat")
        data.append({"id": session.id, "title": title})
    return JsonResponse({"sessions": data})


# =========================================
# ➕ NEW SESSION
# =========================================
@login_required
def new_session(request):
    session = ChatSession.objects.create(user=request.user)
    return JsonResponse({"session_id": session.id})


# =========================================
# 📜 CHAT HISTORY
# =========================================
@login_required
def chat_history(request):
    session_id = request.GET.get("session_id")
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({"history": []})
    chats = ChatHistory.objects.filter(session=session).order_by("created_at")
    data = []
    for chat in chats:
        data.append({
            "id": chat.id,
            "user_message": chat.user_message,
            "bot_response": chat.bot_response
        })
    return JsonResponse({"history": data})


# =========================================
# 📏 DISTANCE CALCULATOR
# =========================================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# =========================================
# 👋 GREETING DETECTION
# =========================================
def is_greeting(message):
    greetings = [
        "hello", "hi", "hey",
        "good morning", "good afternoon", "good evening"
    ]
    message = message.lower().strip()
    return len(message.split()) <= 3 and message in greetings


# =========================================
# 🧠 INTENT DETECTION (IMPROVED)
# =========================================
def detect_intents(message):
    intents = []
    message = message.lower()

    if "side effect" in message:
        intents.append("side_effect")

    if any(word in message for word in ["best", "recommend", "suggest", "which method"]):
        intents.append("recommendation")

    # FIX: Add relationship/preference intents
    if any(word in message for word in ["monogamous", "monogamy", "relationship", "partner", "steady"]):
        intents.append("relationship_preference")

    if any(word in message for word in ["clinic", "hospital", "facility", "health centre", "health center"]):
        intents.append("facility")

    if any(word in message for word in ["nearest", "near", "nearby", "closest"]):
        intents.append("nearest_facility")

    if "free" in message:
        intents.append("free_facility")

    if "private" in message:
        intents.append("private_facility")

    # FIX: Detect requests for general information sources
    if any(word in message for word in ["more information", "where can i get", "learn more", "reliable source"]):
        intents.append("info_source")

    if not intents:
        intents.append("general")
    return intents


# =========================================
# 📚 CONTRACEPTIVE DATA
# =========================================
def get_contraceptive_data(user_message):
    methods = (ContraceptiveMethod.objects.filter(name__icontains=user_message) |
               ContraceptiveMethod.objects.filter(description__icontains=user_message) |
               ContraceptiveMethod.objects.filter(suitability__icontains=user_message))
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


# =========================================
# 🧠 MEMORY
# =========================================
def get_chat_memory(session):
    if not session:
        return ""
    chats = ChatHistory.objects.filter(session=session).order_by("-created_at")[:5]
    history = ""
    for chat in reversed(chats):
        history += f"\nUser: {chat.user_message}\nAssistant: {chat.bot_response}"
    return history


# =========================================
# 🧠 FOLLOW-UP CONTEXT
# =========================================
def build_followup_context(memory):
    memory = memory.lower()
    context = []
    abbreviations = {
        "fams": "Fertility Awareness Methods",
        "iud": "Intrauterine Device",
        "sti": "Sexually Transmitted Infection",
        "larc": "Long Acting Reversible Contraceptive"
    }
    for short, full in abbreviations.items():
        if short in memory:
            context.append(f"{short.upper()} means {full}.")
    if "implant" in memory:
        context.append("Current discussion topic may be contraceptive implant.")
    return "\n".join(context)


# =========================================
# 🚫 DOMAIN FILTER (IMPROVED)
# =========================================
def is_contraceptive_related(message):
    message = message.lower()
    keywords = [
        "contraceptive", "contraception", "family planning", "birth control",
        "pregnancy", "fertility", "condom", "condoms", "pill", "pills",
        "implant", "implants", "iud", "injection", "injectable",
        "side effect", "method", "methods", "recommend", "recommendation",
        "best method", "best contraceptive", "which method", "which contraceptive",
        # FIX: Add relationship / personal context keywords
        "monogamous", "monogamy", "relationship", "partner", "sexually active",
        "trying to conceive", "avoid pregnancy", "birth control options"
    ]
    return any(keyword in message for keyword in keywords)


def extract_current_topic(message):
    message = message.lower()
    topics = ["implant", "implants", "iud", "condom", "pill", "injection", "injectable", "fams", "fertility awareness"]
    for topic in topics:
        if topic in message:
            return topic
    return None


def get_current_topic(session):
    if not session:
        return ""
    chats = ChatHistory.objects.filter(session=session).order_by("-created_at")[:10]
    topics = ["implant", "iud", "condom", "pill", "injection", "fams"]
    for chat in chats:
        text = (chat.user_message + " " + chat.bot_response).lower()
        for topic in topics:
            if topic in text:
                return topic
    return ""


# =========================================
# 🔍 FOLLOW-UP DETECTION
# =========================================
def is_followup_question(message):
    message = message.lower().strip()
    followups = [
        "tell me more", "more information", "more details", "is it safe",
        "how effective", "what about side effects", "what are the side effects",
        "can you explain", "how long does it last", "how does it work",
        "what about this method", "which one"
    ]
    return any(phrase in message for phrase in followups)


# =========================================
# 💡 RECOMMENDATION HANDLER (IMPROVED)
# =========================================
def handle_recommendation(message, session):
    # If the user shared a relationship preference, acknowledge it and ask further
    if "relationship_preference" in detect_intents(message):
        return (
            "Thanks for sharing that you're in a monogamous relationship. "
            "Since STI protection may be less of a concern, we can focus on pregnancy prevention.\n\n"
            "To help me recommend a method, could you tell me:\n"
            "• How old are you?\n"
            "• Do you prefer a daily pill, a long-acting option (like an implant or IUD), or something else?\n"
            "• Would you like a hormone-free method?\n\n"
            "Feel free to answer any of these."
        )

    current_topic = get_current_topic(session)
    if current_topic:
        return (
            "Before recommending a method, can I ask:\n\n"
            "• How old are you?\n"
            "• Are you looking for short-term or long-term protection?\n"
            "• Would you prefer a hormone-free option?\n\n"
            "This helps me recommend a suitable method."
        )
    else:
        # No previous topic – ask general clarifying questions
        return (
            "I'd love to help you find the best contraceptive method.\n\n"
            "Could you tell me a little more about your situation?\n"
            "• Are you in a monogamous relationship?\n"
            "• Do you want to avoid pregnancy, or are you planning for the future?\n"
            "• Would you prefer a daily pill, a long-acting method like an implant, or something else?\n\n"
            "Any detail helps!"
        )


# =========================================
# ℹ️ RELIABLE INFORMATION SOURCES HANDLER (NEW)
# =========================================
def handle_info_source_request():
    return (
        "You can find reliable contraceptive information from:\n\n"
        "📘 **Planned Parenthood** – www.plannedparenthood.org\n"
        "🏥 **CDC Contraception** – www.cdc.gov/reproductivehealth/contraception\n"
        "🌍 **WHO Family Planning** – www.who.int/health-topics/contraception\n"
        "📞 **Your local health department or a family planning clinic**\n\n"
        "Would you like me to list nearby clinics where you can get in‑person counseling?"
    )


# =========================================
# 💡 SUGGESTED REPLIES
# =========================================
def generate_suggested_replies(message):
    message = message.lower()
    if "side effect" in message:
        return [
            "Which methods have fewer side effects?",
            "How long do side effects last?",
            "Are side effects dangerous?"
        ]
    if "recommend" in message or "best" in message:
        return [
            "Which method lasts longest?",
            "Which method is best for students?",
            "Can I switch contraceptive methods?"
        ]
    if any(word in message for word in ["clinic", "hospital", "facility"]):
        return [
            "Show nearby clinics",
            "Which facilities are free?",
            "What services do they offer?"
        ]
    return [
        "What contraceptive methods are available?",
        "Which method has fewer side effects?",
        "Find nearby clinics"
    ]


# =========================================
# 🤖 SYSTEM PROMPT (IMPROVED FOR CONSISTENCY)
# =========================================
def build_system_prompt():
    return """
You are SafeChoice AI, a warm and professional reproductive health assistant.

Rules:
- Be conversational and natural.
- Keep responses concise.
- Use follow-up questions naturally.
- Never repeat greetings unnecessarily.
- Remember abbreviations already introduced.
- Never invent clinics, hospitals, or addresses – only use facility information explicitly provided.
- Avoid robotic responses and long paragraphs unless necessary.
- Politely redirect unrelated conversations.

IMPORTANT – CONSISTENCY:
- If you list side effects for a method (e.g., changes in libido), never later claim the method "does not affect libido". Be consistent.
- If you are unsure about a side effect, say "some users report X, but it varies."

You help with:
- Contraceptive education
- Family planning
- Side effects
- Method recommendations (ask clarifying questions first)
- Nearby reproductive health facilities
"""


# =========================================
# 🤖 CHATBOT RESPONSE (MAIN)
# =========================================
def chatbot_response(request):
    if request.method != "POST":
        return JsonResponse({"response": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
        message = data.get("message", "").strip()
        user_lat = data.get("latitude")
        user_lon = data.get("longitude")
        session_id = data.get("session_id")

        if not message:
            return JsonResponse({"response": "Please enter a message."})

        # ----- GREETING -----
        if is_greeting(message):
            return JsonResponse({
                "response": "Hello 👋 I'm SafeChoice AI. I help with contraceptive methods, family planning information, side effects and nearby reproductive health facilities.\n\nWhat would you like help with today?",
                "suggested_replies": [
                    "What contraceptive methods are available?",
                    "Which method has fewer side effects?",
                    "Find nearby clinics"
                ]
            })

        # ----- SESSION HANDLING -----
        session = None
        if request.user.is_authenticated:
            if session_id:
                try:
                    session = ChatSession.objects.get(id=session_id, user=request.user)
                except ChatSession.DoesNotExist:
                    session = ChatSession.objects.create(user=request.user)
            else:
                session = ChatSession.objects.create(user=request.user)

        memory = get_chat_memory(session)
        intents = detect_intents(message)

        # ----- ENRICH VAGUE FOLLOW-UPS WITH CURRENT TOPIC -----
        current_topic = get_current_topic(session)
        if current_topic and any(word in message.lower() for word in [
            "best", "recommend", "which one", "is it safe",
            "tell me more", "side effects", "more information"
        ]):
            message = f"{message} regarding {current_topic}"

        # ----- DOMAIN CHECK (allows relationship/partner context) -----
        allowed_facility_intents = [
            "facility", "nearest_facility", "free_facility",
            "private_facility", "nearby clinic", "health_facility"
        ]
        if not is_contraceptive_related(message) and not any(i in intents for i in allowed_facility_intents):
            return JsonResponse({
                "response": "I mainly help with contraceptives, family planning, reproductive health and nearby health facilities. Could you tell me what contraceptive information you're looking for?",
                "suggested_replies": [
                    "What contraceptive methods are available?",
                    "What are the side effects?",
                    "Find nearby clinics"
                ]
            })

        # ----- HANDLE "MORE INFORMATION" REQUESTS (reliable sources) -----
        if "info_source" in intents:
            return JsonResponse({
                "response": handle_info_source_request(),
                "suggested_replies": [
                    "Show nearby clinics",
                    "Tell me about implants",
                    "What's the most effective method?"
                ]
            })

        # ----- RECOMMENDATION HANDLER (asks clarifying questions) -----
        if "recommendation" in intents or "relationship_preference" in intents:
            recommendation_response = handle_recommendation(message, session)
            if recommendation_response:
                return JsonResponse({
                    "response": recommendation_response,
                    "suggested_replies": [
                        "I want long-term protection",
                        "I prefer hormone-free methods",
                        "I'm a university student"
                    ]
                })

        response_parts = []

        # ----- FACILITY SEARCH (unchanged, but removed debug prints for clarity) -----
        facility_keywords = ["family planning", "contraceptive", "reproductive", "women", "maternal", "antenatal"]
        facility_queryset = HealthFacility.objects.none()
        for keyword in facility_keywords:
            facility_queryset = facility_queryset | HealthFacility.objects.filter(services__icontains=keyword)
        facility_queryset = facility_queryset.distinct()
        if not facility_queryset.exists():
            facility_queryset = HealthFacility.objects.all()

        facility_response_given = False

        if any(intent in intents for intent in ["facility", "nearest_facility", "free_facility", "private_facility"]):
            queryset = facility_queryset
            if "free_facility" in intents:
                queryset = queryset.filter(offers_free_services=True)
            if "private_facility" in intents:
                queryset = queryset.filter(facility_type__iexact="private")

            if "nearest_facility" in intents and user_lat and user_lon:
                nearby = []
                for facility in queryset:
                    try:
                        if facility.latitude is None or facility.longitude is None:
                            continue
                        distance = calculate_distance(
                            float(user_lat), float(user_lon),
                            float(facility.latitude), float(facility.longitude)
                        )
                        nearby.append((distance, facility))
                    except Exception:
                        continue
                nearby.sort(key=lambda x: x[0])
                if nearby:
                    resp = "🏥 Nearby reproductive health facilities:\n\n"
                    for distance, facility in nearby[:5]:
                        resp += f"{facility.name}\n📍 {facility.location}\n🩺 {facility.services}\n📏 {distance:.2f} km away\n\n"
                    response_parts.append(resp)
                    facility_response_given = True

            if not facility_response_given:
                facilities = list(queryset[:5])
                if facilities:
                    resp = "🏥 Available reproductive health facilities:\n\n"
                    for facility in facilities:
                        resp += f"{facility.name}\n📍 {facility.location}\n🩺 {facility.services}\n\n"
                    response_parts.append(resp)
                    facility_response_given = True
                else:
                    response_parts.append("I could not find reproductive health facilities at the moment.")
                    facility_response_given = True

        # ----- AI RESPONSE (only if not purely facility) -----
        facility_only_request = any(intent in intents for intent in [
            "facility", "nearest_facility", "free_facility", "private_facility"
        ])
        if facility_response_given:
            facility_only_request = True

        if not facility_only_request and not facility_response_given:
            # Enrich short follow-up messages
            if is_followup_question(message):
                topic = get_current_topic(session)
                if topic:
                    message = f"{message} about {topic}"

            contraceptive_context = get_contraceptive_data(message)
            followup_context = build_followup_context(memory)
            system_prompt = build_system_prompt()

            ai_prompt = f"""
SYSTEM:
{system_prompt}

PREVIOUS CONVERSATION:
{memory}

FOLLOW-UP CONTEXT:
{followup_context}

CONTRACEPTIVE KNOWLEDGE:
{contraceptive_context}

IMPORTANT:
- Never invent clinics, hospitals, or addresses.
- Only use facility data supplied by the system.
- Be consistent about side effects (e.g., libido changes).

USER MESSAGE:
{message}
"""
            ai_response = get_ai_response(message, contraceptive_context, ai_prompt)
            response_parts.append(ai_response.strip())

        final_response = "\n\n".join(response_parts)

        # ----- SAVE HISTORY -----
        if request.user.is_authenticated and session:
            ChatHistory.objects.create(
                session=session,
                user_message=message,
                bot_response=final_response
            )

        suggested_replies = generate_suggested_replies(message)
        return JsonResponse({
            "response": final_response,
            "session_id": session.id if session else None,
            "suggested_replies": suggested_replies
        })

    except Exception as e:
        print("CHATBOT ERROR:", str(e))
        return JsonResponse({"response": "Something went wrong. Please try again."})


# =========================================
# 🗑 DELETE MESSAGE
# =========================================
@login_required
@require_POST
def delete_single_message(request):
    try:
        data = json.loads(request.body)
        message_id = data.get("message_id")
        if not message_id:
            return JsonResponse({"status": "error", "message": "Message ID required"})
        ChatHistory.objects.filter(id=message_id, session__user=request.user).delete()
        return JsonResponse({"status": "success", "message": "Message removed successfully"})
    except Exception as e:
        print("DELETE ERROR:", str(e))
        return JsonResponse({"status": "error", "message": "Failed to delete message"})