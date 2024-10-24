from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import QuizImage, PlayerScore
from django.contrib.admin.views.decorators import staff_member_required

import random

def index(request):
    # 상위 10개의 점수를 가져옴
    top_scores = PlayerScore.objects.all()[:10]
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
            # 세션 완전 초기화
            request.session.flush()
            # 새로운 세션 시작
            request.session['player_name'] = player_name
            request.session['score'] = 0
            request.session['question_count'] = 0
            request.session['quiz_ids'] = ''
            request.session.save()
            return JsonResponse({'success': True})
    return JsonResponse({'success': False})
def game(request):
    if 'player_name' not in request.session:
        return redirect('quiz:index')
    
    print("총 문제 수:", QuizImage.objects.count())
    for difficulty in range(1, 6):
        count = QuizImage.objects.filter(difficulty=difficulty).count()
        print(f"난이도 {difficulty}의 문제 수: {count}")
    
    # 세션 초기화가 필요한지 확인
    quiz_ids_str = request.session.get('quiz_ids', '')
    if not quiz_ids_str:  # 빈 문자열이거나 None인 경우
        print("새로운 게임 시작 - 문제 선택")
        request.session['question_count'] = 0
        request.session['score'] = 0
        
        # 난이도별 문제 수
        difficulty_counts = {
            1: 2,  # 매우 쉬움
            2: 4,  # 쉬움
            3: 7,  # 보통
            4: 4,  # 어려움
            5: 3,  # 매우 어려움
        }
        
        # 각 난이도별로 랜덤하게 문제 선택
        selected_questions = []
        for difficulty, count in difficulty_counts.items():
            questions = list(QuizImage.objects.filter(difficulty=difficulty))
            print(f"난이도 {difficulty}에서 선택 가능한 문제 수: {len(questions)}")
            if questions:
                selected_count = min(count, len(questions))
                selected = random.sample(questions, selected_count)
                selected_questions.extend(selected)
                print(f"난이도 {difficulty}에서 선택된 문제 ID들:", [q.id for q in selected])
        
        # 선택된 문제들을 섞어서 세션에 저장
        if selected_questions:
            random.shuffle(selected_questions)
            quiz_ids = [str(q.id) for q in selected_questions]
            quiz_ids_str = ','.join(quiz_ids)
            request.session['quiz_ids'] = quiz_ids_str
            print("최종 선택된 문제 수:", len(quiz_ids))
            print("최종 선택된 문제 ID들:", quiz_ids)
            request.session.save()  # 세션 즉시 저장
    
    # 현재 풀어야 할 문제 가져오기
    quiz_ids = quiz_ids_str.split(',') if quiz_ids_str else []
    print("파싱된 문제 ID들:", quiz_ids)
    
    if quiz_ids and quiz_ids[0]:
        try:
            current_quiz = QuizImage.objects.get(id=int(quiz_ids[0]))
            context = {
                'quiz': current_quiz,
                'score': request.session.get('score', 0),
                'question_count': request.session.get('question_count', 0),
                'total_questions': 20,
                'difficulty': current_quiz.get_difficulty_name()  # 수정된 부분
            }
            print("현재 문제 ID:", current_quiz.id)
        except QuizImage.DoesNotExist:
            print(f"ID {quiz_ids[0]}인 퀴즈를 찾을 수 없습니다.")
            context = {
                'error': '퀴즈를 찾을 수 없습니다. 관리자에게 문의하세요.'
            }
    else:
        print("선택된 문제가 없습니다!")
        context = {
            'error': '등록된 퀴즈가 없습니다. 각 난이도별로 충분한 문제를 등록해주세요.'
        }
    
    return render(request, 'quiz/game.html', context)

def check_answer(request):
    if request.method == 'POST':
        user_answer = request.POST.get('answer', '').strip().lower()
        quiz_id = request.POST.get('quiz_id')
        timeout = request.POST.get('timeout') == 'true'
        skipped = request.POST.get('skipped') == 'true'
        
        try:
            quiz = QuizImage.objects.get(id=quiz_id)
            correct = False
            message = ""
            game_completed = False
            
            # 타임아웃이나 스킵, 또는 정답인 경우에만 문제 카운트 증가
            if timeout or skipped or quiz.answer.lower() == user_answer:
                question_count = request.session.get('question_count', 0) + 1
                request.session['question_count'] = question_count
                
                # 현재 문제 제거 (정답, 타임아웃, 스킵인 경우에만)
                quiz_ids_str = request.session.get('quiz_ids', '')
                quiz_ids = quiz_ids_str.split(',') if quiz_ids_str else []
                if quiz_ids:
                    quiz_ids.pop(0)
                    request.session['quiz_ids'] = ','.join(quiz_ids)
            else:
                # 틀린 경우 현재 문제 유지
                question_count = request.session.get('question_count', 0)
                quiz_ids_str = request.session.get('quiz_ids', '')
                quiz_ids = quiz_ids_str.split(',') if quiz_ids_str else []
            
            # 타임아웃이나 스킵이 아닐 경우에만 정답 체크
            if not timeout and not skipped:
                correct = quiz.answer.lower() == user_answer
                if correct:
                    score = request.session.get('score', 0)
                    request.session['score'] = score + 5
                    message = "정답입니다!"
                else:
                    message = "틀렸습니다. 다시 도전해보세요!"
                    # 틀린 경우 현재 문제를 계속 보여줌
                    return JsonResponse({
                        'correct': correct,
                        'message': message,
                        'score': request.session.get('score', 0),
                        'question_count': question_count,
                        'next_quiz': {
                            'id': quiz.id,
                            'image_url': quiz.image.url,
                            'hint': quiz.hint,
                            'difficulty': quiz.get_difficulty_name()
                        },
                        'game_completed': game_completed
                    })
            elif timeout:
                message = "시간이 초과되었습니다!"
            elif skipped:
                message = "문제를 건너뛰었습니다."
            
            # 20문제 완료 체크
            if question_count >= 20:
                game_completed = True
                player_name = request.session.get('player_name')
                final_score = request.session.get('score', 0)
                
                # 점수 저장
                PlayerScore.objects.create(
                    player_name=player_name,
                    score=final_score
                )
                
                # 세션 초기화
                request.session['question_count'] = 0
                request.session['score'] = 0
                request.session['quiz_ids'] = ''
                
                message = f"게임 완료! 최종 점수는 {final_score}점 입니다!"
                
                return JsonResponse({
                    'correct': correct,
                    'message': message,
                    'score': final_score,
                    'game_completed': True,
                    'final_score': final_score
                })
            
            # 다음 문제 가져오기
            try:
                if quiz_ids and quiz_ids[0]:
                    next_quiz = QuizImage.objects.get(id=int(quiz_ids[0]))
                    return JsonResponse({
                        'correct': correct,
                        'message': message,
                        'score': request.session.get('score', 0),
                        'question_count': question_count,
                        'next_quiz': {
                            'id': next_quiz.id,
                            'image_url': next_quiz.image.url,
                            'hint': next_quiz.hint,
                            'difficulty': next_quiz.get_difficulty_name()
                        },
                        'game_completed': game_completed
                    })
                else:
                    # 문제가 부족한 경우 처리
                    game_completed = True
                    final_score = request.session.get('score', 0)
                    
                    # 점수 저장
                    player_name = request.session.get('player_name')
                    PlayerScore.objects.create(
                        player_name=player_name,
                        score=final_score
                    )
                    
                    # 세션 초기화
                    request.session['question_count'] = 0
                    request.session['score'] = 0
                    request.session['quiz_ids'] = ''
                    
                    return JsonResponse({
                        'error': '더 이상 문제가 없습니다.',
                        'game_completed': True,
                        'final_score': final_score,
                        'message': f"게임 완료! 최종 점수는 {final_score}점 입니다!"
                    })
                
            except QuizImage.DoesNotExist:
                return JsonResponse({
                    'error': '다음 퀴즈를 찾을 수 없습니다.',
                    'game_completed': True,
                    'final_score': request.session.get('score', 0)
                })
                
        except QuizImage.DoesNotExist:
            return JsonResponse({'error': '퀴즈를 찾을 수 없습니다.'})
            
    return JsonResponse({'error': '잘못된 요청입니다.'})