from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import QuizImage, PlayerScore
from django.contrib.admin.views.decorators import staff_member_required
import time
import random

def index(request):
    # 상위 10개의 점수를 가져옴
    top_scores = PlayerScore.objects.all().order_by('-score', '-played_at')[:10]
    return render(request, 'quiz/index.html', {'top_scores': top_scores})

@staff_member_required
def reset_leaderboard(request):
    if request.method == 'POST':
        PlayerScore.objects.all().delete()
        return JsonResponse({'success': True, 'message': '리더보드가 초기화되었습니다.'})
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})

def save_player_name(request):
    if request.method == 'POST':
        player_name = request.POST.get('player_name')
        if player_name:
            request.session.flush()
            request.session['player_name'] = player_name
            request.session['score'] = 0
            request.session['game_start_time'] = time.time()
            request.session['total_solved'] = 0
            request.session['used_quiz_ids'] = []  # 출제된 문제 ID 저장용
            return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def game(request):
    if 'player_name' not in request.session:
        return redirect('quiz:index')
    
    # 게임 시작 시간 체크
    if 'game_start_time' not in request.session:
        request.session['game_start_time'] = time.time()
    
    # 남은 시간 계산 (5분 = 300초)
    elapsed_time = int(time.time() - request.session['game_start_time'])
    remaining_time = max(300 - elapsed_time, 0)
    
    if remaining_time <= 0:
        # 게임 종료 처리
        final_score = request.session.get('score', 0)
        total_solved = request.session.get('total_solved', 0)
        PlayerScore.objects.create(
            player_name=request.session.get('player_name'),
            score=final_score
        )
        request.session.flush()
        return render(request, 'quiz/game_over.html', {
            'score': final_score,
            'total_solved': total_solved
        })
    
    # 사용하지 않은 문제 중에서 랜덤 선택
    used_quiz_ids = request.session.get('used_quiz_ids', [])
    available_quizzes = QuizImage.objects.exclude(id__in=used_quiz_ids)
    
    if available_quizzes.exists():
        quiz = random.choice(available_quizzes)
        # 출제된 문제 ID 저장
        used_quiz_ids = request.session.get('used_quiz_ids', [])
        used_quiz_ids.append(quiz.id)
        request.session['used_quiz_ids'] = used_quiz_ids
        
        context = {
            'quiz': quiz,
            'score': request.session.get('score', 0),
            'total_solved': request.session.get('total_solved', 0),
            'remaining_time': remaining_time,
            'difficulty': quiz.get_difficulty_name()
        }
        return render(request, 'quiz/game.html', context)
    else:
        return render(request, 'quiz/game.html', {
            'error': '더 이상 풀 수 있는 문제가 없습니다.'
        })

def check_answer(request):
    if request.method == 'POST':
        user_answer = request.POST.get('answer', '').strip().lower()
        quiz_id = request.POST.get('quiz_id')
        skipped = request.POST.get('skipped') == 'true'
        
        # 남은 시간 체크
        elapsed_time = int(time.time() - request.session.get('game_start_time', 0))
        remaining_time = max(300 - elapsed_time, 0)
        
        if remaining_time <= 0:
            final_score = request.session.get('score', 0)
            total_solved = request.session.get('total_solved', 0)
            PlayerScore.objects.create(
                player_name=request.session.get('player_name'),
                score=final_score
            )
            request.session.flush()
            return JsonResponse({
                'game_completed': True,
                'message': '시간이 종료되었습니다!',
                'final_score': final_score,
                'total_solved': total_solved
            })
            
        try:
            quiz = QuizImage.objects.get(id=quiz_id)
            
            if not skipped and quiz.answer.lower() == user_answer:
                # 정답 처리 (난이도에 따른 점수 부여)
                score = request.session.get('score', 0)
                request.session['score'] = score + (quiz.difficulty * 10)  # 현재 문제의 난이도로 점수 계산
                request.session['total_solved'] = request.session.get('total_solved', 0) + 1
                message = "정답입니다!"
            elif skipped:
                message = "문제를 건너뛰었습니다."
            else:
                message = "틀렸습니다. 다시 도전해보세요!"
                return JsonResponse({
                    'correct': False,
                    'message': message,
                    'score': request.session.get('score', 0),
                    'total_solved': request.session.get('total_solved', 0),
                    'remaining_time': remaining_time,
                    'next_quiz': {
                        'id': quiz.id,
                        'image_url': quiz.image.url,
                        'hint': quiz.hint,
                        'difficulty': quiz.get_difficulty_name()
                    }
                })
            
            # 다음 문제 선택 (사용하지 않은 문제 중에서 랜덤)
            used_quiz_ids = request.session.get('used_quiz_ids', [])
            available_quizzes = QuizImage.objects.exclude(id__in=used_quiz_ids)
            
            if available_quizzes.exists():
                next_quiz = random.choice(available_quizzes)
                used_quiz_ids.append(next_quiz.id)
                request.session['used_quiz_ids'] = used_quiz_ids
            else:
                # 모든 문제를 다 풀었을 때
                final_score = request.session.get('score', 0)
                total_solved = request.session.get('total_solved', 0)
                PlayerScore.objects.create(
                    player_name=request.session.get('player_name'),
                    score=final_score
                )
                request.session.flush()
                return JsonResponse({
                    'game_completed': True,
                    'message': '모든 문제를 다 푸셨습니다!',
                    'final_score': final_score,
                    'total_solved': total_solved
                })
            
            return JsonResponse({
                'correct': True,
                'message': message,
                'score': request.session.get('score', 0),
                'total_solved': request.session.get('total_solved', 0),
                'remaining_time': remaining_time,
                'next_quiz': {
                    'id': next_quiz.id,
                    'image_url': next_quiz.image.url,
                    'hint': next_quiz.hint,
                    'difficulty': next_quiz.get_difficulty_name()
                }
            })
            
        except QuizImage.DoesNotExist:
            return JsonResponse({'error': '퀴즈를 찾을 수 없습니다.'})
    
    return JsonResponse({'error': '잘못된 요청입니다.'})