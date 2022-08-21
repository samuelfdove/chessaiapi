from flask import request, jsonify, make_response
import chess
from chessAi import findmove

def print_message(FEN):
    FENN = request.args.get('FEN')
    maxtime = int(request.args.get('MAXTIME'))

    bestmove = findmove(FENN,maxtime).uci()
    response = make_response(
        jsonify({"bestmove":bestmove}),
        200,
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


