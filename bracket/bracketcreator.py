from html2image import Html2Image
import numpy as np
import os
import time

def get_cuppicture(arguments):
    title = arguments[1]
    teamarray = arguments[2:]
    teamlength = len(teamarray)
    fillerlength = 1 if teamlength == 0 else 2**(teamlength - 1).bit_length() #get length of teams as the next power of two
    picture_dict = { 32:1120,16:600,8:350,4:250} #height of png to teamsize for example 32 members = 1120px
    heigthcuppic = picture_dict[fillerlength]

    teamarray.extend(['0'] * fillerlength)
    teamarray = teamarray[:fillerlength]
    teamtext = str(np.array(teamarray).reshape(-1, 2).tolist())
    newTeam = teamtext.replace("'0'", "null")

    ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '.'))
    with open(os.path.join(ROOT_DIR, 'results', 'values.js'), "w+") as f:
        f.seek(0)
        f.write(f"var cuptitle = '{title}';")
        f.write("var minimalData = {teams:" + newTeam + "}")
        f.truncate()
        f.close()

    hti = Html2Image(output_path='bracket/results')
    hti.load_file('bracket/templates/jquery-1.6.2.min.js')
    hti.load_file('bracket/templates/jquery.bracket.min.js')
    hti.load_file('bracket/results/values.js')
    cupfilestr = title + "_" + time.strftime("%Y%m%d-%H%M%S") + ".png"
    hti.screenshot(html_file='bracket/templates/elimination.html',css_file="bracket/templates/jquery.bracket.min.css", save_as=cupfilestr , size=(725, heigthcuppic))
    return os.path.join(ROOT_DIR, 'results', cupfilestr)



#commandstring = "seek-cup hotdog seeky grunt silence ramses mirio packer ferreus proraide ploplo klaspes gatts packer ferreus proraide ploplo packer ferreus proraide ploplo klaspes gatts packer ferreus proraide ploplo"
#commandstring = "seek-cup hotdog seeky grunt silence ramses mirio packer ferreus proraide ploplo klaspes gatts packer ferreus proraide ploplo"
#commandstring = "seek-cup hotdog seeky grunt silence ramses mirio packer ferreus"
commandstring = "!cupstart seek-cup hotdog seeky grunt silence"
commandstring = commandstring.split()
print(get_cuppicture(commandstring))