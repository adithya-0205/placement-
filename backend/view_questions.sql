SELECT id, question, area, difficulty, difficulty_level, branch 
FROM questions 
WHERE explanation IS NOT NULL 
LIMIT 10;
