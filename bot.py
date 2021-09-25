from networking.io import Logger
from game import Game
from api import game_util
from model.position import Position
from model.decisions.move_decision import MoveDecision
from model.decisions.action_decision import ActionDecision
from model.decisions.buy_decision import BuyDecision
from model.decisions.harvest_decision import HarvestDecision
from model.decisions.plant_decision import PlantDecision
from model.decisions.do_nothing_decision import DoNothingDecision
from model.tile_type import TileType
from model.item_type import ItemType
from model.crop_type import CropType
from model.upgrade_type import UpgradeType
from model.game_state import GameState
from model.player import Player
from api.constants import Constants

import random
import math

# "Get" global logger and constant
logger = Logger()
constants = Constants()

# Global Variables
# Turn we planted
turn_planted = -1
# Global list of crops we or the opposition have planted at the y,x value
# Both lists are a 50 x 30
# They will be filled with "None" crops at the start of the game
# Friendly will replace "None" crops with crops that we plan
# Opposition will replace "None" crops with crops that we didn't plant
# Neither lists will overlap, the opposing list will have "None" crops in the overlap
friendly_crops = [[]]
opposition_crops = [[]]


def on_better_soil(player, game_state):
    return game_state.tile_map.get_tile(player.pos.x, player.pos.y) >= 5


# Get the x value for the line of ideal crop growth
def get_ideal_y(game_state):
    return math.floor(game_state.turn / 3) - 5


# Check if two crop objects are equal by checking their type, growth_timer, and value
def crop_equals(one, two):
    if not one.type == two.type:
        return False
    if not one.growth_timer == two.growth_timer:
        return False
    if not one.value == two.value:
        return False
    # If made it this far, all variables must be equal so return true
    return True


# Populate the two global crop lists at the beginning of the game
# All crops at the beginning will have crop.type == 9 (the value for no crop type)
def populate_global_crop_lists(game_state):
    # Iterate through all tiles
    for x in range(game_state.tile_map.map_width):
        for y in range(game_state.tile_map.map_height):
            # Populate the crop lists with the initial crops
            friendly_crops[y][x] = game_state.tile_map.get_tile(x, y).crop
            opposition_crops[y][x] = game_state.tile_map.get_tile(x, y).crop


# Check for and update opponent crop list
# If crops have changed since last turn, and we didn't plant them then the crop must be an a opponents
def check_for_opp_crops(game_state):
    # Iterate through all tiles in map
    for x in range(game_state.tile_map.map_width):
        for y in range(game_state.tile_map.map_height):
            # Check that the crop is not one of ours
            if not (friendly_crops[y][x].type == game_state.tile_map.get_tile(x, y).crop.type):
                # Check that the crop is not already updated
                if not (opposition_crops[y][x].type == game_state.tile_map.get_tile(x, y).crop.type):
                    opposition_crops[y][x] = game_state.tile_map.get_tile(x, y).crop


# Update the global crop lists with crop growth
def update_global_tile_lists(game_state):
    for x in range(game_state.tile_map.map_width):
        for y in range(game_state.tile_map.map_height):
            # Check to update the friendly crop
            if not friendly_crops[y][x].type == 9:
                if not crop_equals(friendly_crops[y][x], game_state.tile_map.get_tile(x, y).crop):
                    friendly_crops[y][x] = game_state.tile_map.get_tile(x, y).crop

            # Check to update the opposition crop
            if not opposition_crops[y][x].type == 9:
                if not crop_equals(opposition_crops[y][x], game_state.tile_map.get_tile(x, y).crop):
                    opposition_crops[y][x] = game_state.tile_map.get_tile(x, y).crop


def get_tiles_by_crop(game_state, tiles, crops=[]):
    out_tiles = [[]]
    for x in range(game_state.tile_map.map_width):
        for y in range(game_state.tile_map.map_height):
            if tiles[y][x].crop.type in crops:
                out_tiles[y][x] = tiles[y][x] \
                    if game_state.tile_map.get_tile(x, y).crop.type \
                       in crops else None
    return out_tiles


def get_tiles_with_effects(game_state, tiles, effects=[]):
    out_tiles = [[]]
    for x in range(game_state.tile_map.map_width):
        for y in range(game_state.tile_map.map_height):
            tile_effects = []
            if tiles[y][x].rain_totem_effect:
                effects.append('rain_totem')
            if tiles[y][x].fertility_idol_effect:
                effects.append('fertility_idol')
            if tiles[y][x].scarecrow_totem_effect:
                effects.append('scarecrow')
            for effect in effects:
                out_tiles[y][x] = tiles[y][x] if effect in tile_effects else \
                    None
    return out_tiles


# Returns sorted list of tiles in ascending order by time left for crop to grow
def sort_tiles_by_time(game_state, tiles):
    crops = {}
    for x in range(game_state.tile_map.map_width):
        for y in range(game_state.tile_map.map_height):
            crops[(y, x)] = {'tile': tiles[y][x], 'time':
                tiles[y][x].crop.growth_timer}
    crops_time = sorted(crops.items(), key=lambda x_y: x_y[1]['time'])
    return crops_time


# Determine optimal position to move to in 3 turns
def sort_tiles_by_harvest_value(game, player_pos_x, player_pos_y):
    crops = {}
    game_state = game.get_game_state()
    tiles = game_state.tile_map
    for x in range(game_state.tile_map.map_width):
        for y in range(game_state.tile_map.map_height):
            true_pos = x + y
            near_opp = False
            opp_offset = game_state.get_opponent_player.protection_radius

            if abs(game_state.get_opponent_player.position.y + game_state.get_opponent_player.position.x - true_pos) <= opp_offset:
                near_opp = True
            else:
                pass

            if tiles[y][x].hasScarecrowEffect or near_opp or tiles[y][x].crop.growth_timer > 0:
                val = 0
            else:
                val = tiles[y][x].crop.value
                if is_valid_harvest_pos(Player.harvest_radius, Player.max_movement, player_pos_x, player_pos_y, (x, y)):
                    pass
                else:
                    val *= 0.5
                if tiles[y][x].fertility_idol_effect:
                    val *= 2
                else:
                    pass
                crops[(y, x)] = {'tile': tiles[y][x], 'value': val}

            crops_value = sorted(crops.items(), key=lambda n: n[1]['value'], reverse=True)
            return crops_value


# Determine if the pos you want to move to from player pos is valid
def is_valid_movement_pos(max_movement, player_pos_y, player_pos_x, pos_move=[0, 0]):
    true_pos = distance_to(player_pos_y, player_pos_x, pos_move)
    if true_pos <= max_movement:
        return True
    else:
        return False


def distance_to(player_pos_x, player_pos_y, pos_move=[0, 0]):
    true_pos = abs((player_pos_x + player_pos_y) - (pos_move[0] + pos_move[1]))
    return true_pos


# Move as close to pos_move as possible (within valid space)
def movement_clamp(max_movement, player_pos_x, player_pos_y, pos_move=[0, 0]):
    if is_valid_movement_pos(max_movement, player_pos_x, player_pos_y, pos_move):
        return pos_move[0], pos_move[1]
    elif abs(player_pos_x - pos_move[0]) < max_movement:
        if pos_move[0] == player_pos_x:
            if pos_move[1] > player_pos_y:
                pos_move[1] = player_pos_y + max_movement
            else:
                pos_move[1] = player_pos_y - max_movement
        elif pos_move[0] > player_pos_x:
            pos_move[0] = player_pos_x + max_movement - abs(player_pos_y - pos_move[1])
        else:
            pos_move[0] = player_pos_x - (max_movement - abs(player_pos_y - pos_move[1]))
        return pos_move[0], pos_move[1]
    elif abs(player_pos_y - pos_move[1]) < max_movement:
        if pos_move[1] == player_pos_y:
            if pos_move[1] > player_pos_y:
                pos_move[1] = player_pos_y + max_movement
            else:
                pos_move[1] = player_pos_y - max_movement
        elif pos_move[1] > player_pos_y:
            pos_move[1] = player_pos_y + max_movement - abs(player_pos_x - pos_move[0])
        else:
            pos_move[1] = player_pos_y - (max_movement - abs(player_pos_x - pos_move[0]))
        return pos_move[0], pos_move[1]
    else:
        pos_move[0] = player_pos_x - (max_movement / 2)
        pos_move[1] = player_pos_y - (max_movement / 2)
        if pos_move[1] > player_pos_y:
            pos_move[1] = player_pos_y + max_movement / 2

        if pos_move[0] > player_pos_x:
            pos_move[0] = player_pos_x + max_movement / 2
        else:
            pass
        return pos_move[0], pos_move[1]


def is_valid_harvest_pos(harvest_rad, max_movement, player_pos_x, player_pos_y, pos_move=[0, 0]):
    if distance_to(player_pos_x, player_pos_y, pos_move) < max_movement + harvest_rad:
        return True
    else:
        return False


def is_valid_plant_tiles(game_state: GameState, name: str):
    """
    Returns all tiles for which player of input name can go to
    :param game_state: GameState containing information for the game
    :param name: Name of player to get
    :return: List of positions that the player can harvest
    """
    my_player = game_util.get_player_from_name(game_state, name)
    radius = my_player.plant_radius
    res = []

    for i in range(my_player.position.y - radius, my_player.position.y + radius + 1):
        for j in range(my_player.position.x - radius, my_player.position.x + radius + 1):
            pos = Position(j, i)
            if game_util.distance(my_player.position, pos) <= my_player.plant_radius and game_util.valid_position(pos):
                res.append(pos)
    return res

"""
TOP SECRET CURRENT PLAN(t)
-Do we have seeds?
    -Move to one below ideal
    -Plan seeds
-Else no seeds
    -Did we just plant seeds?
        -Wait or harvest
    -Else already harvested
        -Move to sell
    -Else buy seeds
"""
def get_move_decision(game: Game) -> MoveDecision:
    """
    Returns a move decision for the turn given the current game state.
    This is part 1 of 2 of the turn.

    Remember, you can only sell crops once you get to a Green Grocer tile,
    and you can only harvest or plant within your harvest or plant radius.

    After moving (and submitting the move decision), you will be given a new
    game state with both players in their updated positions.

    :param: game The object that contains the game state and other related information
    :returns: MoveDecision A location for the bot to move to this turn
    """
    # Get the game state from the game
    game_state: GameState = game.get_game_state()
    logger.debug(f"[Turn {game_state.turn}] Feedback received from engine: {game_state.feedback}")
    global turn_planted

    # Select your decision here!
    my_player: Player = game_state.get_my_player()
    pos: Position = my_player.position
    logger.info(f"Currently at {my_player.position}")
    turn = int(game_state.turn)

    # If we have something to sell that we harvested, then try to move towards the green grocer tiles
    if turn < 23:
        x, y = movement_clamp(my_player.max_movement, pos.x, pos.y, [15, 0])
        logger.debug("Moving towards green grocer")
    # If not, move to lower good band
    elif turn > 150:
        x, y = movement_clamp(my_player.max_movement, pos.x, pos.y, [15, 0])
    elif turn_planted + 5 >= game_state.turn:
        x, y = pos.x, pos.y
    # Move toward green grocer if we have harvest, or no seeds
    elif (len(my_player.harvested_inventory)) > 0 or sum(my_player.seed_inventory.values()) == 0:
        x, y = movement_clamp(my_player.max_movement, pos.x, pos.y, [15, 0])

        logger.debug("Moving towards green grocer")

    else:
        x, y = movement_clamp(my_player.max_movement, pos.x, pos.y, [15, get_ideal_y(game_state)+1])
    decision = MoveDecision(Position(x, y))

    logger.debug(f"[Turn {game_state.turn}] Sending MoveDecision: {decision}")
    return decision


def get_action_decision(game: Game) -> ActionDecision:
    """
    Returns an action decision for the turn given the current game state.
    This is part 2 of 2 of the turn.

    There are multiple action decisions that you can return here: BuyDecision,
    HarvestDecision, PlantDecision, or UseItemDecision.

    After this action, the next turn will begin.

    :param: game The object that contains the game state and other related information
    :returns: ActionDecision A decision for the bot to make this turn
    """
    game_state: GameState = game.get_game_state()
    logger.debug(f"[Turn {game_state.turn}] Feedback received from engine: {game_state.feedback}")
    global turn_planted

    # Select your decision here!
    my_player: Player = game_state.get_my_player()
    pos: Position = my_player.position
    # Let the crop of focus be the one we have a seed for, if not just choose a random crop
    crop = max(my_player.seed_inventory, key=my_player.seed_inventory.get) \
        if sum(my_player.seed_inventory.values()) > 0 else random.choice(list(CropType))

    crops_sorted = []
    for i in my_player.seed_inventory.keys():
        if my_player.seed_inventory[i] > 0:
            for j in range(my_player.seed_inventory[i]):
                crops_sorted.append(i)

    # Get a list of possible harvest locations for our harvest radius
    plant_radius = my_player.plant_radius
    possible_plant_locations = []
    possible_harvest_locations = []
    harvest_radius = my_player.harvest_radius
    for harvest_pos in game_util.within_harvest_range(game_state, my_player.name):
        if game_state.tile_map.get_tile(harvest_pos.x, harvest_pos.y).crop.value > 0:
            possible_harvest_locations.append(harvest_pos)
    for plant_pos in is_valid_plant_tiles(game_state, my_player.name):
        possible_plant_locations.append(plant_pos)
    logger.debug(f"Possible harvest locations={possible_harvest_locations}")
    logger.debug(f"Possible plant locations={possible_plant_locations}")
    if my_player.money >= CropType.DUCHAM_FRUIT.get_seed_price() and game_state.tile_map.get_tile(pos.x,pos.y).type == TileType.GREEN_GROCER\
            and my_player.money < 2500:
        if my_player.money >= CropType.GOLDEN_CORN.get_seed_price():
            decision = BuyDecision([CropType.GOLDEN_CORN],
                               [min(int(my_player.money / CropType.GOLDEN_CORN.get_seed_price()), len(my_player.seed_inventory))])
        elif sum(my_player.seed_inventory.values()) < 5:
            decision = BuyDecision([CropType.DUCHAM_FRUIT],
                               [min(int(my_player.money / CropType.DUCHAM_FRUIT.get_seed_price()), len(my_player.seed_inventory))])
        else:
            decision = DoNothingDecision()
    # If we can harvest something, try to harvest it
    elif len(possible_harvest_locations) > 0:
        decision = HarvestDecision(possible_harvest_locations)
    # If not but we have that seed, then try to plant it in a fertility band
    elif len(my_player.seed_inventory) > 0 and \
            game_state.tile_map.get_tile(pos.x, pos.y).type != TileType.GREEN_GROCER and \
            my_player.position.y == get_ideal_y(game_state)+1 and \
            len(possible_plant_locations) > 0 and len(crops_sorted) > 0:
        logger.debug(f"Deciding to try to plant at position {pos}")
        crops = [crop]
        decision = PlantDecision(crops_sorted[0:min(len(crops_sorted), len(possible_plant_locations))], possible_plant_locations[0:len(crops_sorted)])
        turn_planted = game_state.turn
    # If we don't have that seed, but we have the money to buy it, then move towards the
    # green grocer to buy it
    else:
        logger.debug(f"Couldn't find anything to do, waiting for move step")
        decision = DoNothingDecision()

    logger.debug(f"[Turn {game_state.turn}] Sending ActionDecision: {decision}")
    return decision


def main():
    """
    Competitor TODO: choose an item and upgrade for your bot
    """
    game = Game(ItemType.COFFEE_THERMOS, UpgradeType.LONGER_LEGS)

    while True:
        try:
            game.update_game()
        except IOError:
            exit(-1)
        game.send_move_decision(get_move_decision(game))

        try:
            game.update_game()
        except IOError:
            exit(-1)
        game.send_action_decision(get_action_decision(game))


if __name__ == "__main__":
    main()

