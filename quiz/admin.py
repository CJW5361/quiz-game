from django.contrib import admin
from .models import QuizImage, PlayerScore

class QuizImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'answer', 'difficulty', 'hint']
    list_filter = ['difficulty']
    search_fields = ['answer']

admin.site.register(QuizImage, QuizImageAdmin)
admin.site.register(PlayerScore)