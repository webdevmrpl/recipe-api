"""
Serializers for API View
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model


class UserSerializer(serializers.ModelSerializer):
    """ Serializer for user """

    def create(self, validated_data):
        """ Create and return user with encrypted password"""
        return get_user_model().objects.create_user(**validated_data)

    class Meta:
        model = get_user_model()
        fields = ['email', 'name', 'password']
        extra_kwargs = {'password': {'write_only': True, 'min_length': 5}}
