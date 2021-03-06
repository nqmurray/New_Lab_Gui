import tkinter
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation
import os
import time
import threading
from datetime import datetime
from LockinAmp import lockinAmp
from keithley2400 import Keithley2400
from keithley import Keithley
from HP8341 import HP8341

root = Tk()
root.title('ST-FMR Measurement')

global scan_field_output, measured_values, dataplot, freq_lbl

fig = plt.Figure(figsize=(6,5), dpi=100)
ax = fig.add_subplot(111)
scan_field_output = []
measured_values = []
freq_lbl = [0]

def main():

    # plot labels
    plot_title = "Realtime Hall Voltage vs H Plot"
    x_lbl = "Applied Field (Oe)"
    y_lbl = "Lockin Realtime Resistance (Ohm)"

    # dictionaries of GUI contents
    # default initial values
    mag_dict = {
                'Hx Field (Oe)': 1000,
                'Hx Step (Oe)': 100,
                'Output Time (s)': 1
                }

    # set default signal generator settings
    signal_dict = {
                'Power (dBm)': 9.7,
                'Frequency (GHz)': 10,
                'Frequency Step (GHz)': 0
    }

    # default values required for initializing lockin via Pyvisa
    lockin_dict = {
                'Mode': '1st', # Set a default mode (1st or 2nd)
                'Sensitivity': '10mV', # Set a default sensitivity range (mV or uV)
                'Signal Voltage (V)': 0.7, # Set a default OSC signal voltage (V)
                'Frequency (Hz)': 1171, # Set a default OSC frequency (Hz)
                'Average': 3 # number of measurements averaged together
                }

    # values set by various functions, define measurement settings
    control_dict = {
                    'Field Step': 'Step', # set with make_extras()
                    'I_app Step': 'Step', # set with make_extras()
                    'H Output Direction': 'Hx', # set with make_buttons()
                    'Hx DAC Channel': 3, # displayed in make_extras()
                    'Hx/DAC (Oe/V)': 4291.9, # displayed in make_extras()
                    'Hx DAC Limit': 1, # Voltage limit of X direction mag
                    'Display': '', # set with make_info()
                    'File Name': 'Sample Name', # set with make_extras(), used in save function
                    'Directory': ''# set with set_directory(), updated with change_directory()
                    }


    # frames for various widgets
    content = Frame(root)
    plt_frame = Frame(content, borderwidth=10, relief="sunken")
    settings_frame = Frame(content, borderwidth=5)
    information_frame = Frame(content, borderwidth=5)
    buttons_frame = Frame(content, borderwidth=5)
    rows =20

    # grid of above frames
    content.grid(column=0, row=0, sticky='nsew')
    plt_frame.grid(column=0, row=0, columnspan=3, rowspan=rows, sticky='nsew')
    settings_frame.grid(column=3, row=0, columnspan=2, rowspan=rows, sticky='nsew')
    information_frame.grid(column=0, row=rows, columnspan=3, sticky='nsew')
    buttons_frame.grid(column=3, row=rows, columnspan=2, sticky='nsew')

    control_dict['Display'] = make_info(information_frame)
    mag_dict = make_form(settings_frame, mag_dict, 'Magnetic Settings')
    signal_dict = make_form(settings_frame, signal_dict, 'Signal Settings')
    make_lockin(settings_frame, lockin_dict)
    make_extras(settings_frame, mag_dict, control_dict)
    make_plot(plt_frame, plot_title, x_lbl, y_lbl)
    make_buttons(buttons_frame, mag_dict, control_dict, plot_title, x_lbl, y_lbl, lockin_dict, signal_dict)

    #weights columns for all multiple weight=1 columns
    weight(buttons_frame)
    weight(information_frame)
    weight(settings_frame)

    # weights for all rows and columns with weight!=1
    content.columnconfigure(0, weight=3)
    content.columnconfigure(1, weight=3)
    content.columnconfigure(2, weight=3)
    content.columnconfigure(3, weight=1)
    content.columnconfigure(4, weight=1)
    content.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    plt_frame.columnconfigure(0, weight=1)
    plt_frame.rowconfigure(0, weight=1)   
    information_frame.columnconfigure(3, weight=0) # necessary to keep the scroll bar tiny
    information_frame.rowconfigure(0, weight=1)    
    buttons_frame.rowconfigure(0, weight=1)
    #--------end of GUI settings-----------#

    # sets current directory to default (~/Documents/Measurements)
    control_dict['Directory'] = set_directory(control_dict['Display'])

    ani = animation.FuncAnimation(fig, animate, interval=200, fargs=[plot_title, x_lbl, y_lbl])

    root.protocol('WM_DELETE_WINDOW', quit) 
    root.mainloop()
#----------------------------------------END OF MAIN-------------------------------------------#


# animation to plot data
def animate(i, title, x, y):
    global scan_field_output, measured_values, freq_lbl

    ax.clear()
    ax.grid(True)
    ax.set_title(title+'\nMeasurement at '+str(freq_lbl[0])+' GHz')
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.plot(scan_field_output[0:len(measured_values)], measured_values,'b-o', ms=10, mew=0.5)


# takes a given frame and gives all columns a weight of 1
def weight(frame):

    for x in range(frame.grid_size()[0]):
        frame.columnconfigure(x, weight=1)


# takes a dictionary and makes labels and entry widgets for key/value pairs
# returns updated dictionary with entry values
def make_form(root, dictionary, frametxt):

    lf = LabelFrame(root, text=frametxt)
    lf.grid(ipadx=2, ipady=2, sticky='nsew')
    for counter, x in enumerate(dictionary.items()):
        lab = Label(lf, width=20, text=x[0], anchor='w')
        ent = Entry(lf, width=20); ent.insert(0, str(x[1]))
        lab.grid(row=counter, column=0, sticky='nsew')
        ent.grid(row=counter, column=1, sticky='nsew')
        dictionary[x[0]] = ent # set dictionary value to entry widget

    return dictionary


# initializes and grids matplotlib plot 
def make_plot(root, title, x_label, y_label):

    global dataplot

    # canvas for matplotlib gui
    dataplot = FigureCanvasTkAgg(fig, root)
    dataplot.draw()
    dataplot.get_tk_widget().grid(row=0, column=0, pady=0, padx=0, sticky='nsew')


# creates and grids the listbox and scroll bar
def make_info(root):

    listbox = Listbox(root, height=5)
    y_scroll = Scrollbar(root, orient=VERTICAL, command=listbox.yview)
    listbox['yscrollcommand'] = y_scroll.set
    listbox.grid(column=0, row=0, columnspan=3, sticky='nsew')
    y_scroll.grid(column=3, row=0, sticky='ns')

    return listbox


# builds the lockin control GUI panel
def make_lockin(root, lockin_dict):
    lf = LabelFrame(root, text= 'Lockin Settings')
    lf.grid(ipadx=2, ipady=2, sticky='nsew')

    # option menu for Lockin Mode
    lockin_dict['Mode'] = StringVar(); lockin_dict['Mode'].set('1st')
    mode = ttk.OptionMenu(lf, lockin_dict['Mode'], '1st', '1st', '2nd')
    mode_lbl = Label(lf, width=15, text='Mode: ', anchor='w')

    # option menu for Lockin Sensitivity
    lockin_dict['Sensitivity'] = StringVar(); lockin_dict['Sensitivity'].set('10uV')
    sens = ttk.OptionMenu(lf, lockin_dict['Sensitivity'], "10uV","1mV","2mV","5mV","10mV","20mV","50mV","100mV","200mV","10uV","20uV","50uV","100uV")
    sens_lbl = Label(lf, width=15, text='Sensitivity: ', anchor='w')

    #grid the above option menus and labels
    mode_lbl.grid(row=0, column=0, sticky='nsew')
    mode.grid(row=0, column=1, sticky='nsew')
    sens_lbl.grid(row=1, column=0, sticky='nsew')
    sens.grid(row=1, column=1, sticky='nsew')

    # loop over variables that only need entry widgets (excluding first two, initialized above)
    for counter, x in enumerate(lockin_dict.items()):
        if counter > 1:
            lab = Label(lf, width=20, text=x[0], anchor='w')
            ent = Entry(lf, width=20); ent.insert(0, str(x[1]))
            lab.grid(row=counter, column=0, sticky='nsew')
            ent.grid(row=counter, column=1, sticky='nsew')
            lockin_dict[x[0]] = ent # set dictionary value to entry widget


# extra radio buttons and selectors
def make_extras(root, mag_dict, control_dict):

    lf = LabelFrame(root, text='Measurement Options')
    lf.grid(ipadx=2, ipady=2, sticky='nsew')

    # lockin DAC labels
    Hx_lbl = Label(lf, width=20, text=('Hx DAC: %s' % control_dict['Hx DAC Channel']), anchor='w')
    Hx_conv_lbl = Label(lf, width=20, text=('Hx DAC: %s' % control_dict['Hx/DAC (Oe/V)']), anchor='w')
    
    # labels for DAC channels and conversion values, now only editable back end.
    Hx_lbl.grid(row=2, column=0, sticky='nsew')
    Hx_conv_lbl.grid(row=2, column=1, sticky='nsew')

    # file name label and entry
    file_lab = Label(lf, width=20, text='File Name', anchor='w')
    file_ent = Entry(lf, width=20); file_ent.insert(0, control_dict['File Name'])
    file_lab.grid(row=3, column=0, sticky='nsew')
    file_ent.grid(row=3, column=1, sticky='nsew')
    control_dict['File Name'] = file_ent


# creates and grids buttons
def make_buttons(root, mag_dict, control_dict, plot_title, x_lbl, y_lbl, lockin_dict, signal_dict):

    control_dict['H Output Direction'] = StringVar(); control_dict['H Output Direction'].set('Hz')

    # button list
    measure_button = Button(root, text='Measure', \
        command=lambda:measure_method(mag_dict, control_dict, lockin_dict, signal_dict))
    dir_button = Button(root, text='Change Directory', \
        command=lambda:change_directory(control_dict, control_dict['Display']))
    quit_button = Button(root, text='Quit', \
        command=lambda:quit_method(control_dict['Display'], lockin_dict, signal_dict))
    clear_button = Button(root, text='Clear', \
        command=lambda:clear_method(plot_title, x_lbl, y_lbl, control_dict['Display']))
    output_button = Button(root, text='Output', \
        command=lambda:output_method(control_dict, mag_dict, lockin_dict))

    # grid buttons
    output_button.grid(row=0, column=0, columnspan=2, sticky='nsew')
    measure_button.grid(row=1, column =0, columnspan=2, sticky='nsew')
    clear_button.grid(row = 3, column = 0, columnspan=1, sticky='nsew')
    dir_button.grid(row=2, column=0, columnspan=2, sticky='nsew')
    quit_button.grid(row=3, column=1, columnspan=1, sticky='nsew')


# does the matplotlib gui stuff to clear plot area
def plot_set(title, x_label, y_label):

    ax.clear()
    ax.grid(True)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.axis([-1, 1, -1, 1]) 


# sets default save directory, returns directory path
def set_directory(display):

    test = os.path.expanduser('~/Documents')

    if os.path.isdir(test + '/Measurements'):
        os.chdir(test + '/Measurements')
    else:
        os.mkdir(test + '/Measurements')
        os.chdir(test + '/Measurements')

    cur_dir = os.getcwd()

    display.insert('end', 'The current directory is set to: %s' % cur_dir)
    display.see(END)

    return cur_dir


# changes the save directory
def change_directory(control_dict, display):

    control_dict['Directory'] = filedialog.askdirectory()
    display.insert('end', control_dict['Directory'])
    display.see(END)


# applies a field H in the given direction at a given strength
def output_method(control_dict, mag_dict, lockin_dict):
    display = control_dict['Display']
    amp = lockinAmp(lockin_dict['Mode'].get(), lockin_dict['Sensitivity'].get(), float(lockin_dict['Signal Voltage (V)'].get()), int(lockin_dict['Frequency (Hz)'].get()))
    t = mag_dict['Output Time (s)'].get() # output time
    output = mag_dict['Hx Field (Oe)'].get() # output value
    interval = control_dict['Hx/DAC (Oe/V)'] # conversion integral

    # confirms output is number
    if output.lstrip('-').replace('.','',1).isdigit():
        # if output below threshold value, then have lockin amp output for t seconds
        if float(output) / float(interval) < float(control_dict['Hx DAC Limit']):
            amp.dacOutput((float(output) / float(interval)), control_dict['Hx DAC Channel'])
            time.sleep(float(t))
            amp.dacOutput(0, control_dict['Hx DAC Channel'])
            display.insert('end', 'Hx output for %s second(s)' % t)
            display.see(END)
        else:
            messagebox.showwarning('Output Too Large', 'Output value beyond amp voltage threshold')
            display.insert('end', 'Output value too large!')
            display.see(END)
    else:
        messagebox.showwarning('Invalid Entry', 'Output or conversion factor not recognized as a number.')


# clears and redraws the matplotlib gui
def clear_method(title, x_label, y_label, display):

    plot_set(title, x_label, y_label)
    dataplot.show()
    display.delete(0, END)
    print("clear all")


# turns off all outputs and then quits the program
def quit_method(display, lockin_dict, signal_dict):

    global root

    q = messagebox.askquestion('Quit', 'Are you sure you want to quit?')

    if q == 'yes':
        amp = lockinAmp(lockin_dict['Mode'].get(), lockin_dict['Sensitivity'].get(), float(lockin_dict['Signal Voltage (V)'].get()), int(lockin_dict['Frequency (Hz)'].get()))
        amp.dacOutput(0, 1)
        amp.dacOutput(0, 2)
        amp.dacOutput(0, 3)
        amp.dacOutput(0, 4)
        display.insert('end', "All fields set to zero.")
        display.see(END)
        time.sleep(.1)

        root.quit()
    else:
        pass


# takes maximum value and step size and creates a list of all values (floats) to run from low to high
def make_list(max_val, step_val):
    # checks to make sure inputs are valid (numbers)
    if max_val.lstrip('-').replace('.','',1).isdigit() and step_val.lstrip('-').replace('.','',1).isdigit():
        maximum = float(max_val)
        step = float(step_val)
        new_list = []
        # if step is zero, field is only measured at that value
        if step == 0.0:
            return [maximum]
        # if maximum is a positive value, build list from neg to positive
        elif maximum > 0.0:
            maximum = -maximum
            while maximum <= float(max_val):
                new_list.append(maximum)
                maximum += step
            return new_list
        # if maximum is a negative value, build the list
        else:
            while maximum <= -float(max_val):
                new_list.append(maximum)
                maximum += step
            return new_list
    else:
        messagebox.showwarning('Invalid Entry', 'Field or step input is not a digit')


# takes file parameters and results and saves the file, should have 5 lines before data is saved
def save_method(x_values, y_values, display, directory, name, lockin_dict, signal_dict):

    stamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    file = open(str(directory)+"/"+str(name)+"_ST_FMR_"+str(signal_dict['Frequency (GHz)'].get())+"GHz_"+str(signal_dict['Power (dBm)'].get())+"_dBm"+str(stamp), "w")
    file.write("Signal Frequency: "+str(signal_dict['Frequency (GHz)'].get())+"GHz Signal Power: "+str(signal_dict['Power (dBm)'].get())+"dBm\n")
    file.write("Mode: "+str(lockin_dict['Mode'].get())+" Signal Voltage: "+str(lockin_dict['Signal Voltage (V)'])+"V\n")
    file.write("Lockin Frequency: "+str(lockin_dict['Frequency (Hz)'].get())+"Hz\n")
    file.write("Averages: "+ str(lockin_dict['Average'].get())+" Sensitivity: "+str(lockin_dict['Sensitivity'].get())+"\n")
    file.write("Number"+" "+"Hx Field(Oe)"+" "+"Resistance(Ohm)"+"\n")

    for counter, value in enumerate(y_values):
        file.write(str(counter)+" "+str(x_values[counter])+" "+str(value)+"\n")
        
    file.closed

    display.insert('end', stamp)
    display.insert('end', "The Measurement data is saved.")
    display.see(END)


# takes the difference between to scan values and tells how long to rest
def charging(val):
    if val >= 2500:
        return 5.0
    elif 1500 <= val < 2500:
        return 3.0
    elif 1000 <= val < 1500:
        return 1.0
    elif 500 <= val < 1000:
        return 0.5
    elif 100 <= val < 500:
        return 0.25
    elif 50 <= val < 100:
        return 0.1
    else:
        return 0.05

# measurement loop, iterates over values of a list built from parameters in dictionaries
def measure_method(mag_dict, control_dict, lockin_dict, signal_dict):
    
    display = control_dict['Display']

    # target of threading, allows for smooth running
    def measure_loop():
        global scan_field_output, measured_values, freq_lbl

        measured_values = []
        freq_lbl = ['']

        # builds list from step and max value
        scan_field_output = make_list(mag_dict['Hx Field (Oe)'].get(), mag_dict['Hx Step (Oe)'].get())
        # list is built to be negatvie to positive, but measurement needs to be pos to neg
        scan_field_output.reverse()
        # list of frequencies to measure at
        freq_output = make_list(signal_dict['Frequency (GHz)'].get(), signal_dict['Frequency Step (GHz)'].get())


        # ensures output voltages will not exceed amp thresholds
        if max(scan_field_output) / float(control_dict['Hx/DAC (Oe/V)']) < float(control_dict['Hx DAC Limit']) and float(signal_dict['Frequency (GHz)'].get()) < 20:
            
            # initialize machines
            amp = lockinAmp(lockin_dict['Mode'].get(), lockin_dict['Sensitivity'].get(), float(lockin_dict['Signal Voltage (V)'].get()), int(lockin_dict['Frequency (Hz)'].get()))
            sig_gen = HP8341() 
            sig_gen.setPower(float(signal_dict['Power (dBm)'].get())) # set signal gen to power level

            for freq_val in freq_output:

                sig_gen.setFrequency(freq_val) # set frequency
                freq_lbl[0] = freq_val

                # intializes the measurement data list
                measured_values = []

                # measurement loops -  measure pos and neg current at give scan value and take avg abs val (ohms)
                for counter, scan_val in enumerate(scan_field_output):

                    if counter == 0:
                        diff = abs(scan_val)
                    else:
                        diff = abs(scan_val - scan_field_output[counter-1])
                    amp.dacOutput((scan_val / float(control_dict['Hx/DAC (Oe/V)'])), control_dict['Hx DAC Channel'])
                    time.sleep(charging(diff))
                    tmp = 1000 * float(round(amp.readX(lockin_dict['Average'].get()), 4)) # take average from Lockin measurements
                    measured_values.append(tmp)
                    display.insert('end', 'Applied Hx Field Value: %s (Oe)      Measured Resistance: %s (Ohm)' %(scan_val, tmp))
                    display.see(END)

                # save data
                save_method(scan_field_output, measured_values, display, control_dict['Directory'], control_dict['File Name'].get(), lockin_dict, signal_dict)


            # turn everything off at end of loop
            amp.dacOutput(0, control_dict['Hx DAC Channel'])

            display.insert('end',"Measurement finished")
            display.see(END)
        else:
            messagebox.showwarning('Output Too Large', 'Amp Voltage or Signal Frequency Too Large!')
            display.insert('end', 'Output value too large!')
            display.see(END)

        #----------------------------END measure_loop----------------------------------#

    # Only one thread allowed. This is a cheap and easy workaround so we don't have to stop threads
    if threading.active_count() == 1:
        # thread is set to Daemon so if mainthread is quit, it dies
        t = threading.Thread(target=measure_loop, name='measure_thread', daemon=True)
        t.start()
    else:
        messagebox.showerror('Error', 'Multiple threads detected!')


if __name__ == '__main__':
    main()