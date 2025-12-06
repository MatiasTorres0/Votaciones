from rest_framework import serializers
from .models import Pregunta, Opcion

class OpcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Opcion
        fields = '__all__'

class PreguntaSerializer(serializers.ModelSerializer):
    opcion_set = OpcionSerializer(many=True, read_only=True)

    class Meta:
        model = Pregunta
        fields = '__all__'

