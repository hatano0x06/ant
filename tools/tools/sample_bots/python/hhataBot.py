#!/usr/bin/env python
from random import shuffle
from ants import *
import logging
import sys
from optparse import OptionParser
from logutils import initLogging,getLogger

turn_number = 0
bot_version = 'v0.1'

class LogFilter(logging.Filter):
  """
  This is a filter that injects stuff like TurnNumber into the log
  """
  def filter(self,record):
    global turn_number,bot_version
    record.turn_number = turn_number
    record.version = bot_version
    return True

class HHataBot:
    def __init__(self):
        """Add our log filter so that botversion and turn number are output correctly"""        
        log_filter  = LogFilter()
        getLogger().addFilter(log_filter)
        self.visited = [] #keep track of visited row/cols
        self.standing_orders = []
        self.ants_straight = {}
        self.ants_lefty = {}
        self.orders_mode = {} # 1:hill 2:food 3:unseen

    def hunt_hills(self,ants,a_row,a_col,destinations,hunted,orders):
        getLogger().debug("Start Finding Ant")
        closest_enemy_hill = ants.closest_enemy_hill(a_row,a_col)
        getLogger().debug("Done Finding Ant")            
        if closest_enemy_hill!=None:
            return self.do_order(ants, HILL, (a_row,a_col), closest_enemy_hill, destinations, hunted, orders)
            
    def hunt_food(self,ants,a_row,a_col,destinations,hunted,orders):
        getLogger().debug("Start Finding Food")
        closest_food = ants.closest_food(a_row,a_col,hunted)
        getLogger().debug("Done Finding Food")            
        if closest_food!=None:
            return self.do_order(ants, FOOD, (a_row,a_col), closest_food, destinations, hunted, orders)

    def hunt_unseen(self,ants,a_row,a_col,destinations,hunted,orders):
        getLogger().debug("Start Finding Unseen")
        closest_unseen = ants.closest_unseen(a_row,a_col,hunted)
        getLogger().debug("Done Finding Unseen")            
        if closest_unseen!=None:
            return self.do_order(ants, UNSEEN, (a_row,a_col), closest_unseen, destinations, hunted, orders)
    
    def random_move(self,ants,a_row,a_col,destinations,hunted,orders):
        #if we didn't move as there was no food try a random move
        directions = list(AIM.keys())
        getLogger().debug("random move:directions:%s","".join(directions))                
        shuffle(directions)
        getLogger().debug("random move:shuffled directions:%s","".join(directions))
        for direction in directions:
            getLogger().debug("random move:direction:%s",direction)
            (n_row, n_col) = ants.destination(a_row, a_col, direction)
            if (not (n_row, n_col) in destinations and
                    ants.unoccupied(n_row, n_col)):
                return self.do_order(ants, LAND, (a_row,a_col), (n_row, n_col), destinations, hunted, orders)
        
    def do_order(self, ants, order_type, loc, dest, destinations, hunted, orders):
        order_type_desc = ["ant", "hill", "unseen", None, "food", "random", None]
        a_row, a_col = loc
        getLogger().debug("chasing %s:start" % order_type_desc)
        directions = ants.direction(a_row,a_col,dest[0],dest[1])
        getLogger().debug("chasing %s:directions:%s" % (order_type_desc[order_type],"".join(directions)))
        shuffle(directions)
        for direction in directions:
            getLogger().debug("chasing %s:direction:%s" % (order_type_desc[order_type],direction))
            (n_row,n_col) = ants.destination(a_row,a_col,direction)
            if (not (n_row,n_col) in destinations and
                ants.unoccupied(n_row,n_col)):
                ants.issue_order((a_row,a_col,direction))
                getLogger().debug("issue_order:%s,%d,%d,%s","chasing %s" % order_type_desc[order_type],a_row,a_col,direction)                        
                destinations.append((n_row,n_col))
                hunted.append(dest)
                orders.append([loc, (n_row,n_col), dest, order_type])
                return True
        return False
        
    def do_first_order(self,ants,a_row,a_col,destinations,hunted,orders):
    	order = self.orders_mode[(a_row, a_col)]

    	if order == 1:
	        if not self.hunt_hills(ants, a_row, a_col, destinations, hunted, orders):
	        	return False

    	if order == 2:
	        if not self.hunt_food(ants, a_row, a_col, destinations, hunted, orders):
	        	return False

    	if order == 3:
	        if not self.hunt_unseen(ants, a_row, a_col, destinations, hunted, orders):
	        	return False

        return True


    def do_turn(self, ants):
        destinations = []
        new_straight = {}
        new_lefty = {}

        ant_mode = ["hill", "hill", "hill", "unseen", "unseen", "food", "food", "food", "food", "food", ]

        for a_row, a_col in ants.my_ants():
            # first ant
            if (not (a_row, a_col) in self.orders_mode ):
                shuffle(ant_mode)
                if ant_mode[0] == "hill":
                    self.orders_mode[(a_row, a_col)] = 1
                elif ant_mode[0] == "food":
                    self.orders_mode[(a_row, a_col)] = 2
                else:
                    self.orders_mode[(a_row, a_col)] = 3

            # left hand
            # send new ants in a straight line
            if (not (a_row, a_col) in self.ants_straight and
                    not (a_row, a_col) in self.ants_lefty):
                if a_row % 2 == 0:

                    if a_col % 2 == 0:
                        direction = 'n'
                    else:
                        direction = 's'
                else:
                    if a_col % 2 == 0:
                        direction = 'e'
                    else:
                        direction = 'w'
                self.ants_straight[(a_row, a_col)] = direction

            # send ants going in a straight line in the same direction
            if (a_row, a_col) in self.ants_straight:
                direction = self.ants_straight[(a_row, a_col)]
                n_row, n_col = ants.destination(a_row, a_col, direction)
                if ants.passable(n_row, n_col):
                    if (ants.unoccupied(n_row, n_col) and
                            not (n_row, n_col) in destinations):
                        ants.issue_order((a_row, a_col, direction))
                        new_straight[(n_row, n_col)] = direction
                        destinations.append((n_row, n_col))
                    else:
                        # pause ant, turn and try again next turn
                        new_straight[(a_row, a_col)] = LEFT[direction]
                        destinations.append((a_row, a_col))
                else:
                    # hit a wall, start following it
                    self.ants_lefty[(a_row, a_col)] = RIGHT[direction]

            # send ants following a wall, keeping it on their left
            if (a_row, a_col) in self.ants_lefty:
                direction = self.ants_lefty[(a_row, a_col)]
                directions = [LEFT[direction], direction, RIGHT[direction], BEHIND[direction]]
                # try 4 directions in order, attempting to turn left at corners
                for new_direction in directions:
                    n_row, n_col = ants.destination(a_row, a_col, new_direction)
                    if ants.passable(n_row, n_col):
                        if (ants.unoccupied(n_row, n_col) and
                                not (n_row, n_col) in destinations):
                            ants.issue_order((a_row, a_col, new_direction))
                            new_lefty[(n_row, n_col)] = new_direction
                            destinations.append((n_row, n_col))
                            break
                        else:
                            # have ant wait until it is clear
                            new_straight[(a_row, a_col)] = RIGHT[direction]
                            destinations.append((a_row, a_col))
                            break

        # reset lists
        self.ants_straight = new_straight
        self.ants_lefty = new_lefty


                    
if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    try:
        Ants.run(HHataBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')
