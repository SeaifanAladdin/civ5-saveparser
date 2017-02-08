import FileReader as fr
import xml.etree.cElementTree as ET
import pickle

from bitstring import Bits

__author__ = "Hussein Kaddoura"
__copyright__ = "Copyright 2013, Hussein Kaddoura"
__credits__ = ["Hussein Kaddoura"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Hussein Kaddoura"
__email__ = "hussein.nawwaf@gmail.com"
__status__ = "Development"

traits = { 1:"alive",
           3: "human",
           2: "dead",
}

victories = { 1: "VICTORY_TIME",
              2: "VICTORY_SPACE_RACE",
              3: "VICTORY_DOMINATION",
              4: "VICTORY_CULTURAL",
              5: "VICTORY_DIPLOMATIC",
}
v_opt = False
def verbose(string, verboseOn=v_opt):
    if (v_opt): print string
def parse(filename, v_opt):
    """ Parses the save file and transforms it to xml    """
    root = ET.Element("root")

    with fr.FileReader(filename) as civ5Save:
        parse_base(civ5Save, root)
        parse_compressed_payload(civ5Save, root)

    tree = ET.ElementTree(root)
    tree.write(filename + '.transformed.xml')

def parse_base(fileReader, xml):
    """
        Parse the general game options
        Code is definitely not optimal. We'll go through a round a refactoring after mapping more information
        Refactoring 1: Remove all localization queries. This will be done on a later note.
    """

    base = ET.SubElement(xml, 'base')
    version = ET.SubElement(base , 'version')

    fileReader.skip_bytes(4) #always CIV5

    version.set('save', str(fileReader.read_int()))
    version.set('game',fileReader.read_string())
    version.set('build', fileReader.read_string())

    game = ET.SubElement(base, 'game')
    currentturn = str(fileReader.read_int())
    game.set('currentturn', currentturn)
    verbose("current turn: " + currentturn)
    fileReader.skip_bytes(1) #TODO: I'll investigate later as to what this byte hold

    civilization = ET.SubElement(base, 'civilization')
    civilization.text = fileReader.read_string()
    verbose("civilization: " + civilization.text)

    handicap = ET.SubElement(base, 'handicap')
    handicap.text = fileReader.read_string()
    verbose("handicap: " + handicap.text)

    era = ET.SubElement(base, 'era')
    startingEra = fileReader.read_string()
    currentEra = fileReader.read_string()
    era.set('starting', startingEra)
    era.set('current', currentEra)
    verbose("staring era: " + startingEra)
    verbose("current era: " + currentEra)


    gamespeed = ET.SubElement(base, 'gamespeed')
    gamespeed.text = fileReader.read_string()
    verbose("game speed: " + gamespeed.text)

    worldsize = ET.SubElement(base, 'worldsize')
    worldsize.text = fileReader.read_string()
    verbose("worldsize: " + worldsize.text)

    mapscript = ET.SubElement(base, 'mapscript')
    mapscript.text = fileReader.read_string()
    verbose("mapscript: " + mapscript.text)

    fileReader.skip_bytes(4) #TODO: an int
    #
    dlcs = ET.SubElement(base, 'dlcs')
    while fileReader.peek_int() > 2**8:
        fileReader.skip_bytes(16) #TODO: some binary data
        fileReader.skip_bytes(4) #TODO: seems to be always 1
  
        dlc = ET.SubElement(dlcs, 'dlc')
     
        dlc.text = fileReader.read_string()
        verbose("dlc: " + dlc.text)


    fileReader.skip_bytes(4)
    mod = ET.SubElement(base, 'mod')
    while fileReader.peek_int() !=0:
        
        if (fileReader.peek_int() < 2**8):
            modId = fileReader.read_string()
            fileReader.skip_bytes(4)
            modName = fileReader.read_string()
            era.set('modid', modId)
            mod.set('modname', modName)

            
            verbose("mod name: " + modName)
            verbose("mod id: " + modId)
            
            
        else:
            fileReader.skip_bytes(4)
            
       
    
    #
    # #Extract block position (separated by \x40\x00\x00\x00 (@) )
    # #I haven't decoded what each of these blocks mean but I'll extract their position for the time being.

    bit_block_position = tuple(fileReader.findall('0x40000000'))
    #32 blocks have been found. We'll try to map them one at a time.

    #block 1
    fileReader.pos = bit_block_position[0] + 32 #remove the delimiter (@)
    block1 = tuple(map(lambda x: x.read(32).intle, fileReader.read_bytes(152).cut(32)))
    #TODO: block2 - seems to only contain Player 1?

    #block3
    #TODO: Fix leader traits
    #contains the type of civilization - 03 human, 01 alive, 04 missing, 02 dead
    fileReader.pos = bit_block_position[2] + 32
    leader_traits = tuple(map(lambda x: x.read(32).intle, fileReader.read_bytes(256).cut(32)))
    
    #TODO: block4
    #TODO: block5
    #TODO: block6

    #block 7
    # contains the list of civilizations
    civilizations = fileReader.read_strings_from_block(bit_block_position[6] + 32, bit_block_position[7])
    

    #block 8
    #contains the list of leaders
    leaders = fileReader.read_strings_from_block(bit_block_position[7] + 32, bit_block_position[8], True)

    for i in range(len(block1)):
        verbose("civilizations: {0}\t leader: {1}"
                .format(civilizations[i], leaders[i]))
    
    #TODO: block9-18

    #block 19
    # contains the civ states. There seems to be a whole bunch of leading 0s.
    fileReader.forward_to_first_non_zero_byte(bit_block_position[18] + 32, bit_block_position[19])
    civStates = fileReader.read_strings_from_block(fileReader.bits.pos, bit_block_position[19], True)
    for cs in civStates:
        verbose("city states: " + cs)
    #TODO: block 20 - there's a 16 byte long list of 01's
    #TODO: block 21 - seems to be FFs
    #TODO: block 22, 23 - 00s
    #TODO: block 24 - player colors
    #TODO: blocks 25-27

    #block 28
    #the last 5 bytes contain the enabled victory types
    fileReader.pos = bit_block_position[28] - 5*8
    victorytypes = (fileReader.read_byte(), fileReader.read_byte(), fileReader.read_byte(), fileReader.read_byte(), fileReader.read_byte() )
    verbose("victory type: " + str(victorytypes))

    #block 29
    # have the game options
    
    fileReader.find(Bits(bytes=b'GAMEOPTION'), bit_block_position[28] + 32, bit_block_position[29])
    
    fileReader.pos -= 32
    
    gameoptions = []

    #TODO: Fix bug
##    while fileReader.pos < bit_block_position[29]:
##        s = fileReader.read_string()
##        if s == "":
##            break
##        state = fileReader.read_int()
##        verbose(s + ": " + state)
##        gameoptions.append((s, state))

    #TODO: block 30-31

    #TODO: block 32
    #contains the zlib compressed data

    civs = tuple(map(lambda civ, trait, leader:  (civ, trait, leader),civilizations,leader_traits, leaders))

    civsXml = ET.SubElement(base, 'civilizations')
    for civ in civs:
        if civ[1] != 4:
            civXml = ET.SubElement(civsXml, 'civilization')
            civXml.set('name', civ[0])
            ##civXml.set('trait', civ[1])
            civXml.set('leader', civ[2])

    civStatesXml = ET.SubElement(base, 'civStates')
    for civState in civStates:
        civStateXml = ET.SubElement(civStatesXml, 'civState')
        civStateXml.text = civState

    victoriesXml = ET.SubElement(base, 'victories')
    for idx, victory in enumerate(victorytypes, start=1):
        victoriesXml.set(victories[idx], str(victory))

    gameoptionsXml = ET.SubElement(base, 'gameoptions')
    for gameoption in gameoptions:
        gameoptionXml = ET.SubElement(gameoptionsXml, 'gameoption')
        gameoptionXml.set('enabled', str(gameoption[1]))
        gameoptionXml.text = gameoption[0]

def parse_compressed_payload(fileReader, xml):
    files = fileReader.extract_compressed_payloads()

    details = ET.SubElement(xml, 'details')
    with fr.FileReader(files[0]) as f:
        f.read_int() # 1?
        f.read_int() # 0?
        f.read_int() #current turn, already extracted in the main save file
        f.read_int() # 0
        f.read_int() # 0
        f.read_int() # -4000 : starting year?
        f.read_int() # 500  : max turn count?
        f.read_int() # 500 : max turn count?
        playedtime = f.read_int() # playing time in seconds + a last digit

        lastDigit = playedtime % 10
        totalSeconds = int((playedtime - lastDigit) / 10)

        hours, totalSeconds = divmod(totalSeconds , 3600)

        minutes, seconds = divmod(totalSeconds, 60)
        # seconds = (totalSeconds - hours * 3600 - minutes * 60)

        # print(hours, minutes, seconds)

        p = ET.SubElement(details,'timeplayed')
        p.set('hours', str(hours))
        p.set('minutes', str(minutes))
        p.set('seconds', str(seconds))
        p.set('last',str(lastDigit))

        f.read_int() # 0?

        # bunch of bytes. TODO: investigate
        f.skip_bytes(90)

        #comes a list of string stuff.TODO: what do they refer to?
        nb_notes  = f.read_int()
        ns = ET.SubElement(details, 'notes')
        for note in range(0, nb_notes):
            n = ET.SubElement(ns, "note")
            n.text = f.read_string()

        #fast forward to another list skipping some unknown bytes for now
        f.pos = f.find_first('0xC1F2439C016F26110F014A49D3CA01A564ABAD01')[0] + 20 * 8

        #skipping some 20 bytes long blocks
        nb = f.read_int()
        for i in range(0,nb):
            f.skip_bytes(24)

        #get some city stuff notification
        nb_cities = f.read_int()
        citiesXml = ET.SubElement(details, 'citynotes')
        for i in range(0,nb_cities):
            cityXml = ET.SubElement(citiesXml, 'note')
            cityXml.text = f.read_string()

        #get some notes about great persons
        nb_great_persons = f.read_int()
        greatPersonsXml= ET.SubElement(details, 'gpnotes')
        for i in range(0, nb_great_persons):
            gpXml = ET.SubElement(greatPersonsXml, 'note')
            gpXml.text = f.read_string()

        histograms = {}
        histogram_labels = {}

        # histograms data
        # it seems that a lot of this data has been poluted with FFs. I"ll remove them for now.
        histograms_pos = f.findall(b'REPLAYDATASET_SCORE')

        for pos in histograms_pos:
            f.pos = pos + 19*8 #had to skip because of a bug somewhere. TODO: investigate
            # data_sets = f.read_int()
            data_sets = 27 #1B. has to be hardcoded because of a bug somewhere TODO: investigate

            histogram_labels[0] = 'REPLAYDATASET_SCORE'
            histograms[0] = {}

            for i in range(1, data_sets):
                h =  f.read_string_safe()
                histogram_labels[i] = h
                histograms[i] = {}

            n_ent = f.read_byte(3)

            for i in range(0, n_ent):
                n_data = f.read_byte(3)
                for j in range(0, n_data):
                    histograms[i][j] = {}
                    n_turns = f.read_byte(skip=3)
                    if n_turns > 0:
                        for k in range(0, n_turns):
                            turn = f.read_byte(skip=3)
                            value = f.read_byte(skip=3)
                            histograms[i][j][k] = value

            jar = open('histograms.{0}.pickle'.format(pos), 'wb')
            pickle.dump(histograms, jar)
            jar.close()

if __name__ == "__main__":
    import sys
    f_name = sys.argv[1]
    
    if (len(sys.argv) ==3): v_opt = int(sys.argv[2])
    
    parse(f_name, v_opt)
    
