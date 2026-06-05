from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import ChatSession, ChatMessage
from .serializers import ChatSerializer
from .services import generate_response


class ChatAPIView(APIView):

    def post(self, request):

        serializer = ChatSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        session_id = serializer.validated_data["session_id"]
        user_message = serializer.validated_data["message"]

        session, created = ChatSession.objects.get_or_create(
            session_id=session_id
        )

        # Save user message
        ChatMessage.objects.create(
            session=session,
            role="user",
            content=user_message
        )

        # Fetch last 10 messages
        previous_messages = (
            ChatMessage.objects.filter(session=session)
            .order_by("-created_at")[:10]
        )

        history = []

        # Reverse to maintain conversation order
        for msg in reversed(list(previous_messages)):
            history.append({
                "role": msg.role,
                "content": msg.content
            })

        try:

            ai_response = generate_response(
                user_message=user_message,
                history=history
            )

            ChatMessage.objects.create(
                session=session,
                role="assistant",
                content=ai_response
            )

            return Response({
                "success": True,
                "response": ai_response
            })

        except Exception as e:

            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)