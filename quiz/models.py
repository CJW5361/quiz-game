from django.db import models

class QuizImage(models.Model):
    DIFFICULTY_CHOICES = [
        (1, '매우 쉬움'),
        (2, '쉬움'),
        (3, '보통'),
        (4, '어려움'),
        (5, '매우 어려움'),
    ]
    
    image = models.ImageField(upload_to='quiz_images/')
    answer = models.CharField(max_length=100)
    hint = models.CharField(max_length=200, blank=True)
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES, default=1)
    
    def __str__(self):
        return f"퀴즈 {self.id}: {self.answer} (난이도: {self.get_difficulty_display()})"

    def get_difficulty_name(self):
        return dict(self.DIFFICULTY_CHOICES)[self.difficulty]

class PlayerScore(models.Model):
    player_name = models.CharField(max_length=50)
    score = models.IntegerField(default=0)
    played_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-score', '-played_at']
        
    def __str__(self):
        return f"{self.player_name}: {self.score}점"