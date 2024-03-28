"""
Views for user API
"""

from rest_framework import generics
from .serializers import UserSerializer


class CreateUserView(generics.CreateAPIView):
    """ Create new user API """
    serializer_class = UserSerializer
