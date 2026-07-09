from rest_framework import serializers

from apps.leads.models import ContactLead


class ContactLeadSerializer(serializers.ModelSerializer):
    # Honeypot: real users never fill this hidden field. Bots do.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = ContactLead
        fields = (
            "source", "profile", "name", "organization",
            "email", "phone", "message", "locale", "website",
        )

    def validate_website(self, value):
        if value:
            raise serializers.ValidationError("Spam detectado.")
        return value

    def validate(self, attrs):
        source = attrs.get("source", ContactLead.Source.CONTACT)
        # The contact form asks for a name; the waitlist only needs an email.
        if source == ContactLead.Source.CONTACT and not (attrs.get("name") or "").strip():
            raise serializers.ValidationError({"name": "O nome é obrigatório."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("website", None)
        return super().create(validated_data)
