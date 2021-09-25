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

# "Get" global logger and constant
logger = Logger()
constants = Constants()

# Global Variables
# Global list of crops we or the opposition have planted at the y,x value
# Both lists are a 50 x 30
# They will be filled with "None" crops at the start of the game
# Friendly will replace "None" crops with crops that we plan
# Opposition will replace "None" crops with crops that we didn't plant
# Neither lists will overlap, the opposing list will have "None" crops in the overlap
friendly_crops = [[]]
opposition_crops = [[]]

#Check if two crop objects are equal by checking their type, growth_timer, and value
def crop_equals(one, two):
    if not one.type == two.type:
        return False
    if not one.growth_timer == two.growth_timer:
        return False
    if not one.value == two.value:
        return False
    #If made it this far, all variables must be equal so return true
    return True

#Populate the two global crop lists at the beginning of the game
#All crops at the beginning will have crop.type == 9 (the value for no crop type)
def populate_global_crop_lists(game_state):
    # Iterate through all tiles
    for x in range(game_state.tile_map.map_width):
        for y in range(game_state.tile_map.map_height):
            # Populate the crop lists with the intial crops
            friendly_crops[y][x] = game_state.tile_map.get_tile(y, x).crop
            opposition_crops[y][x] = game_state.tile_map.get_tile(y, x).crop


# Check for and update opponent crop list
# If crops have changed since last turn, and we didn't plant them then the crop must be an a opponents
def check_for_opp_crops(game_state):
    # Iterate through all tiles in map
    for x in range(game_state.tile_map.map_width):
        for y in range(game_state.tile_map.map_height):
            # Check that the crop is not one of ours
            if not (friendly_crops[y][x].type == game_state.tile_map.get_tile(y, x).crop.type):
                # Check that the crop is not already updated
                if not (opposition_crops[y][x].type == game_state.tile_map.get_tile(y, x).crop.type):
                    opposition_crops[y][x] = game_state.tile_map.get_tile(y, x).crop


#Update the global crop lists with crop growth
def update_global_tile_lists(game_state):
    for x in range(game_state.tile_map.map_width):
        for y in range(game_state.tile_map.map_height):
            #Check to update the friendly crop
            if not friendly_crops[y][x].type == 9:
                if not crop_equals(friendly_crops[y][x], game_state.tile_map.get_tile(y, x).crop):
                    friendly_crops[y][x] = game_state.tile_map.get_tile(y, x).crop

            #Check to update the opposition crop
            if not opposition_crops[y][x].type == 9:
                if not crop_equals(opposition_crops[y][x], game_state.tile_map.get_tile(y, x).crop):
                    opposition_crops[y][x] = game_state.tile_map.get_tile(y, x).crop



def get_tiles_by_crop(game_state, tiles, crops=[]):
    out_tiles = [[]]
    for x in range(game_state.tile_map.map_width):
        for y in range(game_state.tile_map.map_height):
            if tiles[y][x].crop.type in crops:
                out_tiles[y][x] = tiles[y, x] \
                    if game_state.tile_map.get_tile(x, y).crop.type \
                       in crops else None
    return out_tiles


def get_tiles_with_effects(game_state, tiles, effects=[]):
    out_tiles = [[]]
    for x in range(game_state.tile_map.map_width):
        for y in range(game_state.tile_map.map_height):
            tile_effects = []
            if tiles[y][x].rain_totem_effect is True:
                effects.append('rain_totem')
            if tiles[y][x].fertility_idol_effect is True:
                effects.append('fertility_idol')
            if tiles[y][x].rain_totem_effect is True:
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
    crops_time = sorted(crops.iteritems(), key=lambda x_y: x_y[1]['time'])
    return crops_time


# Determine optimal position to move to in 3 turns
def sort_tiles_by_harvest_value(game, player_pos_y, player_pos_x):
    out_tiles = [[]]
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

            if tiles.get_tile[y][x].scarecrowEffect == True or near_opp or tiles.get_tile[y][x].crop.growth_timer > 0:
                val = 0
            else:
                val = tiles.get_tile[y][x].crop.value
                if is_valid_movement_pos(Player.max_movement, player_pos_y, player_pos_x, y, x):
                    pass
                else:
                    val *= 0.5
                if tiles.get_tile[y][x].fertility_idol_effect:
                    val *= 2
                else:
                    pass
                crops[(y, x)] = {'tile': tiles.get_tile[y][x], 'value': val}

            crops_value = sorted(crops.iteritems(), key=lambda n: n[1]['value'],reverse=True)
            return crops_value

def distance_to(player_pos_y, player_pos_x, pos_move=(0, 0)):
    true_pos = str((player_pos_x + player_pos_y) - (pos_move[0] + pos_move[1]))
    if true_pos.contains("-"):
        true_pos.strip("-")
    return int(true_pos)


#Determine if the pos you want to move to from player pos is valid
def is_valid_movement_pos(max_movement, player_pos_y, player_pos_x, pos_move=(0, 0)):
    true_pos = distance_to(player_pos_y, player_pos_x, pos_move)
    if true_pos <= max_movement:
        return True
    else:
        return False

def is_valid_harvest_pos(harvest_rad,max_movement, player_pos_y, player_pos_x, pos_move=(0, 0)):
    if distance_to(player_pos_y, player_pos_x, pos_move)<max_movement:
    elif pos_move[0]
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
    game_state: GameState = game.get_game_state()
    logger.debug(f"[Turn {game_state.turn}] Feedback received from engine: {game_state.feedback}")

    # Select your decision here!
    my_player: Player = game_state.get_my_player()
    pos: Position = my_player.position
    logger.info(f"Currently at {my_player.position}")

    # If we have something to sell that we harvested, then try to move towards the green grocer tiles
    if random.random() < 0.5 and \
            (sum(my_player.seed_inventory.values()) == 0 or
             len(my_player.harvested_inventory)):
        logger.debug("Moving towards green grocer")
        decision = MoveDecision(Position(constants.BOARD_WIDTH // 2, max(0, pos.y - constants.MAX_MOVEMENT)))
    # If not, then move randomly within the range of locations we can move to
    else:
        pos = random.choice(game_util.within_move_range(game_state, my_player.name))
        logger.debug("Moving randomly")
        decision = MoveDecision(pos)
    # Move towards oppositions crops
    if len(opposition_crops) > 0:
        xPos = opposition_crops[0][0]
        yPos = opposition_crops[0]
        while not is_valid_movement_pos(player_pos_y= pos.y, player_pos_x= pos.x, pos_move= (xPos, yPos)):
            xPos =


    if (len(my_player.harvest_inventory) + 8) > my_player.carring_capacity:
        decision = MoveDecision(Position(15, 0))

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

    # Select your decision here!
    my_player: Player = game_state.get_my_player()
    pos: Position = my_player.position
    # Let the crop of focus be the one we have a seed for, if not just choose a random crop
    crop = max(my_player.seed_inventory, key=my_player.seed_inventory.get) \
        if sum(my_player.seed_inventory.values()) > 0 else random.choice(list(CropType))

    # Get a list of possible harvest locations for our harvest radius
    possible_harvest_locations = []
    harvest_radius = my_player.harvest_radius
    for harvest_pos in game_util.within_harvest_range(game_state, my_player.name):
        if game_state.tile_map.get_tile(harvest_pos.x, harvest_pos.y).crop.value > 0:
            possible_harvest_locations.append(harvest_pos)

    logger.debug(f"Possible harvest locations={possible_harvest_locations}")

    # If we can harvest something, try to harvest it
    if len(possible_harvest_locations) > 0:
        decision = HarvestDecision(possible_harvest_locations)
    # If not but we have that seed, then try to plant it in a fertility band
    elif my_player.seed_inventory[crop] > 0 and \
            game_state.tile_map.get_tile(pos.x, pos.y).type != TileType.GREEN_GROCER and \
            game_state.tile_map.get_tile(pos.x, pos.y).type.value >= TileType.F_BAND_OUTER.value:
        logger.debug(f"Deciding to try to plant at position {pos}")
        friendly_crops[pos.y][pos.x] = crop
        decision = PlantDecision([crop], [pos])
    # If we don't have that seed, but we have the money to buy it, then move towards the
    # green grocer to buy it
    elif my_player.money >= crop.get_seed_price() and \
            game_state.tile_map.get_tile(pos.x, pos.y).type == TileType.GREEN_GROCER:
        logger.debug(f"Buy 1 of {crop}")
        decision = BuyDecision([crop], [1])
    # If we can't do any of that, then just do nothing (move around some more)
    else:
        logger.debug(f"Couldn't find anything to do, waiting for move step")
        decision = DoNothingDecision()

    logger.debug(f"[Turn {game_state.turn}] Sending ActionDecision: {decision}")
    return decision


def main():
    """
    Competitor TODO: choose an item and upgrade for your bot
    """
    game = Game(ItemType.COFFEE_THERMOS, UpgradeType.SCYTHE)

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
