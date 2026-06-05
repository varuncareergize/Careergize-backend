from rest_framework import serializers


class ChatSerializer(serializers.Serializer):

    session_id = serializers.CharField()

    message = serializers.CharField()