import chess
import time

def f(b):
    b.push(chess.Move(chess.F3,chess.F7))


b = chess.Board('r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5Q2/PPPP1PPP/RNB1KBNR w KQkq - 2 3')
print(b.is_check())
f(b)
print(b.is_check())

t0 = time.time()
time.sleep(5)
print(time.time()-t0)

