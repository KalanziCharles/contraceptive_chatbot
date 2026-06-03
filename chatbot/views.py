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

    return render(
        request,
        "chatbot/signup.html",
        {"form": form}
    )


# =========================================
# 🔐 LOGIN
# =========================================
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

    sessions = ChatSession.objects.filter(
        user=request.user
    ).order_by("-updated_at", "-id")

    data = []

    for session in sessions:

        first_chat = ChatHistory.objects.filter(
            session=session
        ).order_by("id").first()

        title = (
            first_chat.user_message[:40]
            if first_chat else "New Chat"
        )

        data.append({
            "id": session.id,
            "title": title
        })

    return JsonResponse({
        "sessions": data
    })


# =========================================
# ➕ NEW SESSION
# =========================================
@login_required
def new_session(request):

    session = ChatSession.objects.create(
        user=request.user
    )

    return JsonResponse({
        "session_id": session.id
    })


# =========================================
# 📜 CHAT HISTORY
# =========================================
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


# =========================================
# 📏 DISTANCE CALCULATOR
# =========================================
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


# =========================================
# 👋 GREETING DETECTION
# =========================================
def is_greeting(message):

    greetings = [
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "good evening"
    ]

    message = message.lower().strip()

    return (
        len(message.split()) <= 3
        and message in greetings
    )


# =========================================
# 🧠 INTENT DETECTION
# =========================================
def detect_intents(message):

    intents = []

    message = message.lower()

    if "side effect" in message:
        intents.append("side_effect")

    if any(word in message for word in [
        "best",
        "recommend",
        "suggest",
        "which method"
    ]):
        intents.append("recommendation")

    if any(word in message for word in [
        "clinic",
        "hospital",
        "facility",
        "health centre",
        "health center"
    ]):
        intents.append("facility")

    if any(word in message for word in [
        "nearest",
        "near",
        "nearby",
        "closest"
    ]):
        intents.append("nearest_facility")

    if "free" in message:
        intents.append("free_facility")

    if "private" in message:
        intents.append("private_facility")

    if not intents:
        intents.append("general")

    return intents


# =========================================
# 📚 CONTRACEPTIVE DATA
# =========================================
def get_contraceptive_data(user_message):

    methods = (
        ContraceptiveMethod.objects.filter(
            name__icontains=user_message
        )
        |
        ContraceptiveMethod.objects.filter(
            description__icontains=user_message
        )
        |
        ContraceptiveMethod.objects.filter(
            suitability__icontains=user_message
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


# =========================================
# 🧠 MEMORY
# =========================================
def get_chat_memory(session):

    if not session:
        return ""

    chats = ChatHistory.objects.filter(
        session=session
    ).order_by("-created_at")[:5]

    history = ""

    for chat in reversed(chats):

        history += f"""
User: {chat.user_message}
Assistant: {chat.bot_response}
"""

    return history


# =========================================
# 🧠 FOLLOW-UP CONTEXT
# =========================================
def build_followup_context(memory):

    memory = memory.lower()

    context = []

    if "fertility awareness methods" in memory:
        context.append(
            "FAMs means Fertility Awareness Methods."
        )

    if "iud" in memory:
        context.append(
            "IUD means Intrauterine Device."
        )

    if "implant" in memory:
        context.append(
            "The implant is a long-term contraceptive inserted in the arm."
        )

    return "\n".join(context)


# =========================================
# 🚫 DOMAIN FILTER
# =========================================
def is_contraceptive_related(message):

    keywords = [
        "contraceptive",
        "family planning",
        "birth control",
        "pregnancy",
        "fertility",
        "condom",
        "pill",
        "iud",
        "implant",
        "injection",
        "ovulation",
        "reproductive",
        "menstrual",
        "side effects",
        "fams"
    ]

    message = message.lower()

    return any(
        keyword in message
        for keyword in keywords
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

    if any(word in message for word in [
        "clinic",
        "hospital",
        "facility"
    ]):
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
# 🤖 SYSTEM PROMPT
# =========================================
def build_system_prompt():

    return """
You are SafeChoice AI, a warm and professional reproductive health assistant.

Rules:
- Be conversational and natural
- Keep responses concise
- Use follow-up questions naturally
- Never repeat greetings unnecessarily
- Remember abbreviations already introduced
- Never invent clinics or hospitals
- Never invent addresses
- Only use facility information explicitly provided
- Avoid robotic responses
- Avoid long paragraphs unless necessary
- Politely redirect unrelated conversations

You help with:
- Contraceptive education
- Family planning
- Side effects
- Method recommendations
- Nearby reproductive health facilities
"""


# =========================================
# 🤖 CHATBOT RESPONSE
# =========================================
def chatbot_response(request):

    if request.method != "POST":

        return JsonResponse({
            "response": "Invalid request"
        }, status=400)

    try:

        data = json.loads(request.body)

        message = data.get(
            "message",
            ""
        ).strip()

        user_lat = data.get("latitude")
        user_lon = data.get("longitude")

        session_id = data.get("session_id")

        if not message:

            return JsonResponse({
                "response": "Please enter a message."
            })

        # =====================================
        # GREETING
        # =====================================
        if is_greeting(message):

            return JsonResponse({
                "response":
                    "Hello 👋 I'm SafeChoice AI. "
                    "I help with contraceptive methods, "
                    "family planning information, side effects "
                    "and nearby reproductive health facilities.\n\n"
                    "What would you like help with today?",
                "suggested_replies": [
                    "What contraceptive methods are available?",
                    "Which method has fewer side effects?",
                    "Find nearby clinics"
                ]
            })

        # =====================================
        # SESSION HANDLING
        # =====================================
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

        # =====================================
        # MEMORY
        # =====================================
        memory = get_chat_memory(session)

        # =====================================
        # INTENTS
        # =====================================
        intents = detect_intents(message)

        # =====================================
        # DOMAIN CHECK
        # =====================================
        allowed_facility_intents = [
            "facility",
            "nearest_facility",
            "free_facility",
            "private_facility"
             "nearby clinic"
             "health_facility"
        ]

        if (
            not is_contraceptive_related(message)
            and
            not any(
                i in intents
                for i in allowed_facility_intents
            )
        ):

            return JsonResponse({
                "response":
                    "I mainly help with contraceptives, "
                    "family planning, reproductive health "
                    "and nearby health facilities.",
                "suggested_replies": [
                    "What contraceptive methods are available?",
                    "What are the side effects?",
                    "Find nearby clinics"
                ]
            })

        response_parts = []

        # =====================================
        # FACILITY SEARCH
        # =====================================

        facility_keywords = [
            "family planning",
            "contraceptive",
            "reproductive",
            "women",
            "maternal",
            "antenatal"
        ]

        facility_queryset = HealthFacility.objects.all()

        # Fallback to all facilities if keyword search finds none
        if not facility_queryset.exists():
            facility_queryset = HealthFacility.objects.all()

        facility_response_given = False

        # =====================================
        # FACILITY REQUESTS
        # =====================================

        if any(intent in intents for intent in [
            "facility",
            "nearest_facility",
            "free_facility",
            "private_facility"
        ]):

            queryset = facility_queryset

            # ------------------------------
            # FREE FACILITIES
            # ------------------------------
            if "free_facility" in intents:
                queryset = queryset.filter(
                    offers_free_services=True
                )

            # ------------------------------
            # PRIVATE FACILITIES
            # ------------------------------
            if "private_facility" in intents:
                queryset = queryset.filter(
                    facility_type__iexact="private"
                )

            # ------------------------------
            # NEARBY FACILITIES
            # ------------------------------
            if (
                "nearest_facility" in intents and
                user_lat and
                user_lon
            ):

                nearby = []

                for facility in queryset:

                    try:

                        if (
                            facility.latitude is None or
                            facility.longitude is None
                        ):
                            continue

                        distance = calculate_distance(
                            float(user_lat),
                            float(user_lon),
                            float(facility.latitude),
                            float(facility.longitude)
                        )

                        nearby.append(
                            (distance, facility)
                        )

                    except Exception as e:
                        print(
                            f"Distance error for "
                            f"{facility.name}: {e}"
                        )
                        continue

                nearby.sort(
                    key=lambda x: x[0]
                )

                if nearby:

                    response = (
                        "🏥 Nearby reproductive "
                        "health facilities:\n\n"
                    )

                    for distance, facility in nearby[:5]:

                        response += (
                            f"{facility.name}\n"
                            f"📍 {facility.location}\n"
                            f"🩺 {facility.services}\n"
                            f"📏 {distance:.2f} km away\n\n"
                        )

                    response_parts.append(response)

                    facility_response_given = True

            # ------------------------------
            # FALLBACK
            # NO LOCATION OR NO DISTANCES
            # ------------------------------
            if not facility_response_given:

                facilities = list(
                    queryset[:5]
                )

                if facilities:

                    response = (
                        "🏥 Available reproductive "
                        "health facilities:\n\n"
                    )

                    for facility in facilities:

                        response += (
                            f"{facility.name}\n"
                            f"📍 {facility.location}\n"
                            f"🩺 {facility.services}\n\n"
                        )

                    response_parts.append(
                        response
                    )

                    facility_response_given = True

                else:

                    response_parts.append(
                        "I could not find reproductive "
                        "health facilities at the moment."
                    )

                    facility_response_given = True

        # =====================================
        # AI RESPONSE
        # =====================================
        facility_only_request = any(
            intent in intents
            for intent in [
                "facility",
                "nearest_facility",
                "free_facility",
                "private_facility"
            ]
        )

        # Only generate AI response when
        # request is not purely facility-related
        if (
            not facility_only_request
            and
            not facility_response_given
        ):

            contraceptive_context = (
                get_contraceptive_data(message)
            )

            followup_context = (
                build_followup_context(memory)
            )

            system_prompt = (
                build_system_prompt()
            )

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
        - Never invent clinics
        - Never invent hospitals
        - Never invent addresses
        - Only use facility data supplied by the system

        USER MESSAGE:
        {message}
        """

            ai_response = get_ai_response(
                message,
                contraceptive_context,
                ai_prompt
            )

            response_parts.append(
                ai_response.strip()
            )

        # =====================================
        # FINAL RESPONSE
        # =====================================
        response = "\n\n".join(response_parts)

        # =====================================
        # SAVE HISTORY
        # =====================================
        if (
            request.user.is_authenticated
            and session
        ):

            ChatHistory.objects.create(
                session=session,
                user_message=message,
                bot_response=response
            )

        # =====================================
        # SUGGESTED REPLIES
        # =====================================
        suggested_replies = (
            generate_suggested_replies(
                message
            )
        )

        return JsonResponse({
            "response": response,
            "session_id":
                session.id if session else None,
            "suggested_replies":
                suggested_replies
        })

    except Exception as e:

        print(
            "CHATBOT ERROR:",
            str(e)
        )

        return JsonResponse({
            "response":
                "Something went wrong. "
                "Please try again."
        })


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

            return JsonResponse({
                "status": "error",
                "message": "Message ID required"
            })

        ChatHistory.objects.filter(
            id=message_id,
            session__user=request.user
        ).delete()

        return JsonResponse({
            "status": "success",
            "message":
                "Message removed successfully"
        })

    except Exception as e:

        print(
            "DELETE ERROR:",
            str(e)
        )

        return JsonResponse({
            "status": "error",
            "message":
                "Failed to delete message"
        })