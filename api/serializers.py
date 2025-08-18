from rest_framework import serializers

from crawler.models import Medicine, Generic, DrugClass, DosageForm, Indication, Manufacturer


class MedicineSerializer(serializers.ModelSerializer):
    generic_name = serializers.ReadOnlyField(source='generic.generic_name', read_only=True)
    manufacturer_name = serializers.ReadOnlyField(source='manufacturer.manufacturer_name', read_only=True)

    class Meta:
        model = Medicine
        exclude = ('created', 'updated', 'generic', 'manufacturer')


class GenericSerializer(serializers.ModelSerializer):
    medicines = MedicineSerializer(many=True, read_only=True)

    class Meta:
        model = Generic
        exclude = ('created', 'updated')


class DrugClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrugClass
        exclude = ('created', 'updated')


class IndicationSerializer(serializers.ModelSerializer):
    generics = GenericSerializer(many=True, read_only=True)

    class Meta:
        model = Indication
        exclude = ('created', 'updated')


class DosageFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = DosageForm
        exclude = ('created', 'updated')


class ManufacturerSerializer(serializers.ModelSerializer):
    medicines = MedicineSerializer(many=True, read_only=True)

    class Meta:
        model = Manufacturer
        exclude = ('created', 'updated')
