import chess
import chess.pgn
import random
import chess.polyglot
import time
from zobristfunctions import makezobrist,board2zobrist2,makezobristmove3,makezobristmoveandmaterial
from piecesquaretables import alll

#opening book reader
reader = chess.polyglot.open_reader("baron30.bin")

#initializing zobrist arrays and values
def initialize():

    global zarray
    global transtable
    global gamezvals

    #this will hold the list of zvals for the move stack
    gamezvals = []

    #making the array holding the 64bit number for each piece and each square
    zarray = makezobrist()

    #making 100k table for transposition
    transtable = [[] for i in range(100000)]

#function to return the right score if the game is over
def gameover(boardd):
    result = boardd.outcome().result()
    turn = boardd.turn
    
    if result == "1-0":
        if turn:
            return 100000000
        else:
            return -100000000
    elif result == "0-1":
        if turn:
            return -100000000
        else:
            return 100000000
    else:
        #this is a draw
        return 0  


#this will sort the moves for better alpha beta pruning, determine viable moves for quice search, and find the zval, materialadvantage,piece-square eval, and overall evaluation of all new moves 
def sorting2(boardd,zval,materialadv,piecesquareeval,quiece,alpha,oldlegalmoves = [],oldevals = []):
    legalmoves = list(boardd.legal_moves)
    zvals = []
    materials = []
    piecesquares = []
    evals = []


    newlegal = list()
    i = 0

    #iterating through each move
    for move in legalmoves:

        #not considering moves not in quice search parameters (if it is quice search)
        if (quiece and (boardd.is_capture(move) or boardd.gives_check(move) or boardd.is_check())) or (not quiece):

            newzval,newmaterial,newpiecesquareeval = makezobristmove3(boardd,move,zval,zarray,materialadv,piecesquareeval,alll)
            evall = evaluation(boardd,newmaterial,newpiecesquareeval)

            #delta pruning: only considering quice moves if it raises alpha
            if evall>alpha or not quiece:

                newlegal.append(move)
                zvals.append(newzval)
                materials.append(newmaterial)
                piecesquares.append(newpiecesquareeval)

                #if there are previous move lists from transposition tables, we add the higher eval for better move ordering and pruning.
                if len(oldevals)>i and len(oldlegalmoves)>i:
                    if oldlegalmoves[i] == move and oldevals[i]>evall:
                        evals.append(oldevals[i])
                    else:
                        evals.append(evall)
                else:
                    evals.append(evall)
        i+=1

    
    if len(newlegal)>0:
        #sorting moves by evaluations from highest to lowest
        sortedevals,sortedmaterials,sortedpiecesquares,sortedzval,sortedlegal = zip(*sorted(zip(evals,materials,piecesquares,zvals,newlegal),reverse=True))  
    else: 
        sortedevals,sortedmaterials,sortedpiecesquares,sortedzval,sortedlegal = [],[],[],[],[]

    #print(len(sortedlegal),len(sortedzval),len(sortedmaterials),len(sortedpiecesquares),len(sortedevals))
    return list(sortedlegal),list(sortedzval),list(sortedmaterials),list(sortedpiecesquares),list(sortedevals)

#alpha beta pruning, will return move evaluation
def alphabeta(boardd,zval,materialadv,piecesquareeval,depth,alpha,beta):

    #stopping search once max time is reached
    global t0
    global maxtime
    if time.time()-t0 > maxtime:
        raise NameError('timeout')

    #ogalpha is used to know if a search has failed-low
    ogalpha = alpha

    evals = []
    #if printlogs: movestack = boardd.move_stack
    #if printlogs: print("STARTING move:",boardd.ply(),"inside alphabeta, depth:",depth,"movestack:",movestack[len(movestack)-depthh+depth-1:len(movestack)],file=log)
   
    #checking if game is over
    if boardd.is_game_over():
        evall = gameover(boardd)
        #if printlogs: print("found game over, returning:",evall,file=log)
        
        return evall+depth

    #cheking transposition table
    global transtable
    FEN = boardd.fen()
    legalmoves = []

    table = transtable[zval%len(transtable)]
    if not table == []:
        
        #table row is the same board position (based on zval)
        if zval==table[0]:

            #throwing error if zval matches but FENs don't
            if table[1][0:table[1].index(' ')]!=FEN[0:FEN.index(' ')]:
                print('ERROR:',table[1],":",FEN)
            else:
                if table[2] >= depth:
                    #table[6] = cut type: 1=pure value, 2=cut (beta cutoff, fail high), 3=all (alpha cutoff, fail low)
                    #table[7] = ogalpha
                    #table[8] = beta
                    #table[3] = stored value
                    if table[6] == 1: #exact node
                        if table[3] >= beta:
                            return beta
                        if table[3] <= alpha:
                            return alpha
                        return table[3]
                    elif table[6] == 2: #lower bound
                        if table[3]>=beta:
                            return beta
                        if table[3]> alpha:
                            alpha = table[3]
                    elif table[6] == 3: #upper bound:
                        if table[3] <= alpha:
                            return alpha
                        if table[3] > beta:
                            beta=table[3]

                #getting legal moves and evals for pruning
                legalmoves = table[4]
                evals = table[5]
    
    
    #quiesce search at end of depth
    if depth ==0:
        quick = quiesce(boardd,zval,materialadv,piecesquareeval,alpha, beta )
        #if printlogs: print("at depth 0, quicksearch:",quick,file=log)
        return quick


    #sorting
    legalmoves,zvals,materials,piecesquares,evalss = sorting2(boardd,zval,materialadv,piecesquareeval,False,alpha,legalmoves,evals)

    #going through all moves
    for i in range(len(legalmoves)):
        move = legalmoves[i]
        #newzval,newmaterial,newpiecesquareeval = makezobristmove3(boardd,move,zval,zarray,materialadv,piecesquareeval,alll)
        boardd.push(move)
        score =  -alphabeta(boardd,zvals[i],materials[i],piecesquares[i],depth-1, -beta, -alpha)
        evals.append(score)

        if score >= beta: #beta cutoff
            boardd.pop()
            #if printlogs: print("found score:",score,">=beta:",beta,file=log)

            #storing into transposition table for beta cutoff (node type 2)
            transtable[zval%len(transtable)] = [zval,FEN,depth,beta,legalmoves,evals,2,ogalpha,beta]
            return beta
        if score > alpha:
            alpha = score;
        boardd.pop()

    #if printlogs: print("LEAVING move:",boardd.ply(),"inside alphabeta, depth:",depth,"movestack:",movestack[len(movestack)-depthh+depth-1:len(movestack)],"eval:",alpha,file=log)
    #if printlogs: print("legalmoves:",legalmoves,"evals:",evals,file=log)

    #putting entry into table:
    if ogalpha != alpha: transtable[zval%len(transtable)] = [zval,FEN,depth,alpha,legalmoves,evals,1,ogalpha,beta]
    else: transtable[zval%len(transtable)] = [zval,FEN,depth,alpha,legalmoves,evals,3,ogalpha,beta]

    return alpha

def quiesce(boardd,zval,materialadv,piecesquareeval,alpha,beta):

    #stopping search once max time is reached
    global t0
    global maxtime
    if time.time()-t0 > maxtime:
        raise NameError('timeout')
    

    ogalpha = alpha
    FEN = boardd.fen()
    global rootmove
    #if printlogs: movestack = boardd.move_stack
    #if printlogs: print("\tquiesce:",boardd.ply(),"materialadv:",materialadv,"alpha:",alpha,"beta",beta,"FEN",FEN,file=log)

    if boardd.is_game_over():
        evall = gameover(boardd)
        #if printlogs: print("found game over, returning:",eval,file=log)
        return evall


    table = transtable[zval%len(transtable)]
    legalmoves = []
    evals = []
    if not table == []:
        if zval==table[0]:
            if table[1][0:table[1].index(' ')]!=FEN[0:FEN.index(' ')]:
                print('ERROR QUICK:',table[1],":",FEN)
            else:
                if table[2] >= -1:
                    #table[6] = cut type: 1=pure value, 2=cut (beta cutoff, fail high), 3=all (alpha cutoff, fail low)
                    #table[7] = ogalpha
                    #table[8] = beta
                    #table[3] = stored value
                    if table[6] == 1:
                        if table[3] >= beta:
                            return beta
                        if table[3] <= alpha:
                            return alpha
                        return table[3]
                    if table[6] == 2: #lower bound
                        if table[3]>=beta:
                            return beta
                        if table[3]> alpha:
                            alpha = table[3]
                    elif table[6] == 3: #upper bound:
                        if table[3] <= alpha:
                            return alpha
                        if table[3] > beta:
                            beta=table[3]
                legalmoves = table[4]
                evals = table[5]

    #getting stand_pat evaluation as an eval.  If the player is in check, we are not counting stand pat
    if not boardd.is_check():
        stand_pat = evaluation(boardd,materialadv,piecesquareeval)
        #print("\t\tERROR CHECK: ",boardd.is_check(),"     ", not boardd.is_check(),file=log)
        if stand_pat >= beta:
            #if printlogs: print("\tquiesce:",boardd.ply(),"found stand_pat:",stand_pat,">= beta:",beta,"returning beta",file=log)
            return beta
        if alpha < stand_pat:
            #if printlogs: print("\tquiesce: alpha:",alpha,"<",stand_pat,"alpha=stand_pat",file=log)
            alpha=stand_pat
        evals = [stand_pat]
    else:
        evals = []
        
    #sorting
    legalmoves,zvals,materials,piecesquares,evalss = sorting2(boardd,zval,materialadv,piecesquareeval,True,alpha,legalmoves,evals)
    #legalmoves = list(boardd.legal_moves)
    
    
    
    for i in range(len(legalmoves)):
        move = legalmoves[i]
        #if printlogs: print("\tquiesce:",boardd.ply(),'testing out next move:',move,file=log)
        boardd.push(move)
        score = -quiesce(boardd,zvals[i],materials[i],piecesquares[i],-beta,-alpha)
        evals.append(score)
        boardd.pop()

        if score >= beta:
            #if printlogs: print("\tquiesce:",boardd.ply(),"score:",score,">=beta",beta,"returning beta",file=log)
            
            #storing into transposition table for beta cutoff (node type 2)
            transtable[zval%len(transtable)] = [zval,FEN,-1,beta,legalmoves,evals,2,ogalpha,beta]
            
            return beta
        if score > alpha:
            alpha=score

    #if printlogs: print("\tquiesce:",boardd.ply(),"leaving with score:",alpha,file=log)
    if ogalpha != alpha: transtable[zval%len(transtable)] = [zval,FEN,-1,alpha,legalmoves,evals,1,ogalpha,beta]
    else: transtable[zval%len(transtable)] = [zval,FEN,-1,alpha,legalmoves,evals,3,ogalpha,beta]
    return alpha

#getting evaluation score based on material advantage and piece locations
def evaluation(boardd,materialadv,piecesquareeval):
    
    if boardd.is_game_over():
        evall = gameover(boardd)
        #if printlogs: print("found game over, returning:",eval,file=log)
        return evall

    #adjusting eval based on if it's white or blacks turn
    if boardd.turn:
        #if printlogs: print(boardd.fen(),'white to move, eval:',materialadv*1000,file=log)
        return materialadv*1000+piecesquareeval
    else:
        #if printlogs: print(boardd.fen(),'black to move, eval:',-materialadv*1000,file=log)
        return -materialadv*1000-piecesquareeval

#function used in API, returns bestmove
def findmove(FEN,maxtimei):
    #initializes zobrist stuff
    initialize()
    boardd = chess.Board(FEN)

    #returning book move if available
    if reader.get(boardd) != None:
        return reader.find(boardd).move


    global maxtime
    maxtime = maxtimei

    #getting initial zvalues based on position
    global zarray
    zval,materialadv,piecesquareeval = board2zobrist2(boardd,zarray,alll)

    legalmoves = list(boardd.legal_moves)
    evals = []
    lenlegal = len(legalmoves)

    #returning move if there is only 1 move possible
    if lenlegal == 1:
        return legalmoves[0]


    global rootmove
    rootmove = len(boardd.move_stack)
    global transtable

    #iterative deepening part, starting with depth1 and increasing
    depth = 1
    global t0
    t0 = time.time()
    ogbestmove = None
    try: #try: is for stopping at maxtime, see below for catch
        while depth<=50 and time.time()-t0<maxtimei:
            #t00 = time.time()
            #if printlogs: print("NEW DEPTH: ",depth,file=log)
            #cheking transtable
            
            FEN = boardd.fen()
            table = transtable[zval%len(transtable)]
            #getting initial evaluation for sorting
            rooteval = evaluation(boardd,materialadv,piecesquareeval)

            #transpostion table
            if not table == []:
                if zval==table[0]:
                    if table[1][0:table[1].index(' ')]!=FEN[0:FEN.index(' ')]:
                        print('ERROR:',table[1],":",FEN)
                    else:
                        legalmoves = table[4]
                        evals = table[5]
                        rooteval = table[3]

            alpha = -999999999
            #sorting based on previous depth
            legalmoves,zvals,materials,piecesquares,evalss = sorting2(boardd,zval,materialadv,piecesquareeval,False,alpha,legalmoves,evals)


            loopnum = 0
            alpha = None
            beta=None
            bestmove = None
            alphawindow = 0
            betawindow = 0

            #aspiration windows, starting with narrow window and expanding if alpha or beta cutoff
            while bestmove==None:
                allevals = []
                
                #isBetabreak determines if the search failed high (research necessary)
                isBetabreak = False

                #setting aspiration window, it goes up 10 fold each time
                alpha = rooteval - 3*(10**alphawindow)
                beta = rooteval + 3*(10**betawindow)
                ogalpha = alpha
                #if printlogs: print("NEW ROUND: alpha = ",alpha," beta = ",beta,file=log)

                #going through each move
                for i in range(lenlegal):
                    move = legalmoves[i]
                    #newzval,newmaterial,newpiecesquareeval = makezobristmove3(boardd,move,zval,zarray,materialadv,piecesquareeval,alll)
                    boardd.push(move)

                    #not playing repetitions
                    #TODO: change this so computer can draw by repition if adventagious
                    if boardd.is_repetition(2):
                        boardd.pop()

                    else:
                        evall = -alphabeta(boardd,zvals[i],materials[i],piecesquares[i],depth,-beta,-alpha)
                        allevals.append(evall)
                        #print(evall,alpha,beta,evall>alpha)

                        #fail high (need research), exiting loop
                        if evall>=beta:
                            bestmove=None
                            isBetabreak=True
                            boardd.pop()
                            break
                        if evall>alpha and evall != beta:
                            alpha=evall
                            bestmove = move
                        boardd.pop()
                
                loopnum+=1
                if bestmove==None: #failing low or high
                    
                    #fail high, increasing beta
                    if isBetabreak:
                        betawindow+=1
                    #fail low
                    else:
                        alphawindow+=1
                
                #move found!
                elif bestmove != None:
                    #print(ogalpha,beta,allevals)
                    ogbestmove = bestmove
                    transtable[zval%len(transtable)] = [zval,FEN,depth+1,alpha,legalmoves,allevals,1,ogalpha,beta]
            #print(depth,loopnum,ogalpha,beta,bestmove.uci(),time.time()-t00)
            depth+=1
    
    #time out, returning previous move
    except NameError:
        if ogbestmove != None:
            return ogbestmove
        else:
            return legalmoves[0]

    return bestmove

#playselfgame, only used in debugging/running locally
def playselfgame():
    initialize()
    boardd = chess.Board()
    #game values are to show up on board, but that is commented out for API purposes
    game = chess.pgn.Game()
    game.setup(boardd)  
    node = game
    #display.start(chess.Board().fen())
    #display.start('r2r4/1p1nqp1k/4p1pp/1KppP3/3P2RP/6QN/PPP2PP1/2R5 b - - 149 117')
    while not boardd.is_game_over():
        if printlogs: 
            global log
            #log = open("logtest.txt",'w')
            #logname = "logs/log_"+str(boardd.ply())+".txt"
            #log = open(logname,'w')
        #bestmove = rootsearch(boardd,depthh)
        bestmove = findmove(boardd.fen())
        node = node.add_variation(bestmove)
        boardd.push(bestmove)
        #if printlogs: print(boardd,file=log)
        #if printlogs: print("\n\n",file=log)
        #display.start(boardd.fen())
        print(game)
        initialize()
        #display.update('r2r4/1p1nqp1k/4p1pp/1KppP3/3P2RP/6QN/PPP2PP1/2R5 b - - 149 117')
    print(game)
    print('#################')
    print('DONE')
    print(boardd.result())

def continualgames():
    while True:
        playselfgame()

#test for debugging
def testmove(FEN,depth):
    printlogs=True
    initialize()
    board = chess.Board(FEN)
    zval,materialadv,piecesquareval = board2zobrist2(board,zarray,alll)
    print(materialadv)
    global log
    #log = open("logtest.txt",'w')
    #move =(rootsearch(board,depth))
    move = findmove(FEN)
    print(move)
    newzval,newmaterial,newpiecesquareeval = makezobristmove3(board,move,zval,zarray,materialadv,piecesquareval,alll)
    print(newmaterial)

#playselfgame()

# x = findmove("r1bq1b1r/ppp1k1p1/3ppn1p/5p2/3PB3/2N1PN2/PPPB1PPP/R2Q1RK1 b - - 0 12")

#OLD FUNCTIONS

#searching first level of moves, returning best move.
#This is now no longer in use due to findmove() replacing it with iterative deepening
def rootsearch(boardd,depth,alpha=-999999999,beta=999999999):

    #'''
    if reader.get(boardd) != None:
        print('book move')
        return reader.choice(boardd).move
    #'''

    global zarray
    zval,materialadv,piecesquareval = board2zobrist2(boardd,zarray,alll)

    
    ogalpha = alpha

    legalmoves = list(boardd.legal_moves)
    lenlegal = len(legalmoves)

    if lenlegal == 1:
        return legalmoves[0]


    #need to add pruning / move ordering, should be pretty easy, might move the makezobristmoveandmaterial function
    allevals = []
    bestmove = None

    global rootmove
    rootmove = len(boardd.move_stack)
    for i in range(lenlegal):
        move = legalmoves[i]
        newzval,newmaterial,newpiecesquareeval = makezobristmove3(boardd,move,zval,zarray,materialadv,piecesquareval,alll)
        boardd.push(move)
        if boardd.is_repetition(2):
            boardd.pop()
        else:
            evall = -alphabeta(boardd,newzval,newmaterial,newpiecesquareeval,depth,-beta,-alpha)
            allevals.append(evall)
            if evall>alpha:
                alpha=evall
                bestmove = move
 
            boardd.pop()
    
    
    #if printlogs: print("LEGAL MOVES:",legalmoves,"EVALS:",allevals,file=log)
    #if printlogs: print("SENDING MOVE:",boardd.ply(),"eval:",alpha,'move:',bestmove,file=log)

    
    transtable[zval%len(transtable)] = [zval,boardd.fen(),depth+1,alpha,legalmoves,allevals,1,ogalpha,beta]
    
    return bestmove

#OLD SORTING FUNCTION
#TODO: Delete and retest
def sorting(boardd,zval,materialadv,piecesquareeval,quiece,alpha):
    legalmoves = list(boardd.legal_moves)
    zvals = []
    materials = []
    piecesquares = []
    evals = []
    

    newlegal = list()
    for move in legalmoves:
        
        if (quiece and (boardd.is_capture(move) or boardd.gives_check(move) or boardd.is_check())) or (not quiece):
            newzval,newmaterial,newpiecesquareeval = makezobristmove3(boardd,move,zval,zarray,materialadv,piecesquareeval,alll)
            evall = evaluation(boardd,newmaterial,newpiecesquareeval)
            if evall>alpha or not quiece: #evall<alpha):
                newlegal.append(move)
                zvals.append(newzval)
                materials.append(newmaterial)
                piecesquares.append(newpiecesquareeval)
                evals.append(evall)

    if len(newlegal)>0:
        sortedevals,sortedmaterials,sortedpiecesquares,sortedzval,sortedlegal = zip(*sorted(zip(evals,materials,piecesquares,zvals,newlegal),reverse=True))  
    else: 
        sortedevals,sortedmaterials,sortedpiecesquares,sortedzval,sortedlegal = [],[],[],[],[]

    #print(len(sortedlegal),len(sortedzval),len(sortedmaterials),len(sortedpiecesquares),len(sortedevals))
    return list(sortedlegal),list(sortedzval),list(sortedmaterials),list(sortedpiecesquares),list(sortedevals)
