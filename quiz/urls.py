from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path('', views.index, name='index'),
    path('save-player-name/', views.save_player_name, name='save_player_name'),
    path('game/', views.game, name='game'),
    path('check-answer/', views.check_answer, name='check_answer'),
    path('reset-leaderboard/', views.reset_leaderboard, name='reset_leaderboard'),
]
