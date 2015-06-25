
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np

from bemio.data_structures import bem

class WamitOutput(object):
    '''
    Class to read and interact with WAMIT simulation data
    
    **Inputs:**

    * out_file: Absolute or relative loaction and name of the WAMIT .out file
    * density: fluid denisty (default:1000.)

    '''
    def __init__(self, out_file, density=1000., gravity=9.81):

        self.files = bem.generate_file_names(out_file)
        
        self.rho = density
        self.g = gravity

        self.data = {}
        self._read()

    def _read(self):
        '''
        Internal function to read WAMIT output file into the class. that is called during __init__
        '''
        with open(self.files['out'],'rU') as fid:

            raw = fid.readlines()
   
        code = 'WAMIT'
        num_bodies = 0 # Total number of bodies
        bod_count = 0 # Counter for bodies
        freq_count = 0
        T = []
        cg = {}
        cb = {}
        name = {}    
        disp_vol = {}
        k = {}
        wave_dir = []
        empty_line = '\n'

        
        for i, line in enumerate(raw):



            if "POTEN run date and starting time:" in line:

                data = raw[i+4]
                count = 0

                while data != empty_line:

                    count += 1
                    T.append(float(data.split()[0]))
                    data = raw[i+count+4]

            if "Wave Heading (deg)" in line:
                wave_dir.append(float(line.split()[-1]))       
            
            if 'Water depth:' in line:
                water_depth = raw[i].split()[2]
                try:
                    water_depth = np.float(water_depth)
                except:
                    pass 

            # If there is one body in the WAMIT run
            if "Input from Geometric Data File:" in line:

                num_bodies = 1
                name[0] = raw[i].split()[-1]

            
            # If there are two bodies in the WAMIT run
            if "Input from Geometric Data Files:" in line:

                for j in xrange(20): # look for bodies within the next 20 lines

                    if "N=" in raw[i+j]:

                        num_bodies += 1
                        name[num_bodies-1] = raw[i+j].split()[-1]


            # Read the body positions
            if "Total panels:" in line:

                for j in xrange(15): # look for position within the next 15 lines - will only work for wamit files of about 5 bodies

                    if 'XBODY =' in raw[i+j]:
                        '''
                        Note that this is the XBOD YBOD ZBOD defined in the wamit .out file, not the cg as defined in the wamit file
                        '''

                        temp = raw[i+j].split()
                        cg[bod_count] = np.array([temp[2],temp[5],temp[8]]).astype(float)
                        
                    if 'Volumes (VOLX,VOLY,VOLZ):' in raw[i+j]:

                        temp = raw[i+j].split()
                        disp_vol[bod_count] = float(temp[-1])
                        
                    if 'Center of Buoyancy (Xb,Yb,Zb):' in raw[i+j]:

                        temp = raw[i+j].split()
                        cb[bod_count] = np.array([temp[-3],temp[-2],temp[-1]]).astype(float)
                        
                    if 'C(3,3),C(3,4),C(3,5):' in raw[i+j]:

                        temp = np.zeros([6,6])
                        temp2 = raw[i+j].split()
                        temp[2,2] = np.float(temp2[1])
                        temp[2,3] = np.float(temp2[2])
                        temp[2,4] = np.float(temp2[3])
                        
                        temp2 = raw[i+j+1].split()
                        temp[3,3] = np.float(temp2[1])
                        temp[3,4] = np.float(temp2[2])
                        temp[3,5] = np.float(temp2[3])
                        
                        temp2 = raw[i+j+2].split()
                        temp[4,4] = np.float(temp2[1])
                        temp[4,5] = np.float(temp2[2])
                        
                        k[bod_count] = temp
                        

                bod_count += 1      
                        
        # Put things into numpy arrays                               
        T = np.array(T).astype(float)
        wave_dir = np.array(wave_dir).astype(float)

        # Only select the wave headings once
        temp = 999999
        temp_wave_dir = []
        count = 0

        while temp != wave_dir[0]:

            count += 1
            temp_wave_dir.append(wave_dir[count-1])
            temp = wave_dir[count]


        wave_dir = np.array(temp_wave_dir).astype(float)

        # Read added mass and rad damping
        count_freq = 0
        am_all = np.zeros([6*num_bodies,6*num_bodies,T.size])
        rd_all = am_all.copy()
        am_inf = np.zeros([6*num_bodies,6*num_bodies])
        am_zero = am_inf.copy()

        for i, line in enumerate(raw):

            # Read inf freq added mass
            if "Wave period = zero" in line:
                
                count = 7
                temp_line = raw[count+i]

                while temp_line != empty_line:

                    am_inf[int(temp_line.split()[0])-1,int(temp_line.split()[1])-1] = temp_line.split()[2]
                    count += 1
                    temp_line = raw[count+i]


            # Read zero freq added mass
            if "Wave period = infinite" in line:
                
                count = 7
                temp_line = raw[count+i]

                while temp_line != empty_line:

                    am_zero[int(temp_line.split()[0])-1,int(temp_line.split()[1])-1] = temp_line.split()[2]
                    count += 1
                    temp_line = raw[count+i]


            # Read freq dependent added mass and rad damping
            if "Wave period (sec) =" in line:

                count = 7
                temp_line = raw[count+i]

                while temp_line != empty_line:

                    am_all[int(temp_line.split()[0])-1,int(temp_line.split()[1])-1,count_freq] = temp_line.split()[2]
                    rd_all[int(temp_line.split()[0])-1,int(temp_line.split()[1])-1,count_freq] = temp_line.split()[3]
                    count += 1 
                    temp_line = raw[count+i]
                
                count_freq += 1


        # Terribly complicated code to read excitation forces and phases, RAOs, etc
        ex_all = np.zeros([6*num_bodies,wave_dir.size,T.size])
        phase_all = ex_all.copy()
        rao_all = ex_all.copy()
        rao_phase_all = ex_all.copy()
        ssy_all = ex_all.copy()
        ssy_phase_all = ex_all.copy()
        count_diff2 = 0
        count_rao2 = 0
        count_ssy2 = 0
        for i, line in enumerate(raw):

            count_diff = 0
            count_rao = 0
            count_ssy = 0

            if "DIFFRACTION EXCITING FORCES AND MOMENTS" in line:

                count_diff += 1
                count_diff2 += 1
                count_wave_dir = 0
                count = 0

                while count_wave_dir < wave_dir.size:

                    count += 1

                    if "Wave Heading (deg) :" in raw[i+count_diff + count]:

                        count_wave_dir += 1
                        temp_line = raw[i+count_diff+count+4]
                        count2 = 0

                        while temp_line != empty_line:
                            count2 += 1
                            ex_all[int(temp_line.split()[0])-1,count_wave_dir-1,count_diff2-1] = float(temp_line.split()[1])
                            phase_all[int(temp_line.split()[0])-1,count_wave_dir-1,count_diff2-1] = float(temp_line.split()[2])
                            temp_line = raw[i+count_diff+count+4+count2]

            if "RESPONSE AMPLITUDE OPERATORS" in line:

                count_rao += 1
                count_rao2 += 1
                count_wave_dir = 0
                count = 0

                while count_wave_dir < wave_dir.size:

                    count += 1

                    if "Wave Heading (deg) :" in raw[i+count_rao + count]:

                        count_wave_dir += 1
                        temp_line = raw[i+count_rao+count+4]
                        count2 = 0

                        while temp_line != empty_line:
                            count2 += 1
                            rao_all[int(temp_line.split()[0])-1,count_wave_dir-1,count_rao2-1] = float(temp_line.split()[1])
                            rao_phase_all[int(temp_line.split()[0])-1,count_wave_dir-1,count_rao2-1] = float(temp_line.split()[2])
                            temp_line = raw[i+count_rao+count+4+count2]

            if "SURGE, SWAY & YAW DRIFT FORCES (Momentum Conservation)" in line:

                count_ssy += 1
                count_ssy2 += 1
                count_wave_dir = 0
                count = 0

                while count_wave_dir < wave_dir.size:

                    count += 1

                    if "Wave Heading (deg) :" in raw[i+count_ssy + count]:

                        count_wave_dir += 1
                        temp_line = raw[i+count_ssy+count+4]
                        count2 = 0

                        while temp_line != empty_line:
                            count2 += 1
                            ssy_all[int(temp_line.split()[0])-1,count_wave_dir-1,count_ssy2-1] = float(temp_line.split()[1])
                            ssy_phase_all[int(temp_line.split()[0])-1,count_wave_dir-1,count_ssy2-1] = float(temp_line.split()[2])
                            temp_line = raw[i+count_ssy+count+4+count2]


        # Load data into the hydrodata structure
        for i in xrange(num_bodies):       
            self.data[i] = bem.HydrodynamicData() 
            self.data[i].name = name[i][0:-4]
            self.data[i].g = self.g
            self.data[i].water_depth = water_depth
            self.data[i].rho = self.rho            
            self.data[i].num_bodies = num_bodies
            self.data[i].body_num = i
            self.data[i].cg = cg[i] 
            self.data[i].cb = cb[i]
            self.data[i].k = k[i]
            #self.data[i].k = self.data[i].k*self.rho*self.g
            self.data[i].disp_vol = disp_vol[i]
            self.data[i].wave_dir = wave_dir
            self.data[i].T = T
            self.data[i].w = 2.0*np.pi/self.data[i].T
            
            if 'am_inf' in locals():

                self.data[i].am.inf = am_inf[6*i:6+6*i,:]
                # self.data[i].am.inf = self.data[i].am.inf*self.rho

            else:

                self.data[i].am.inf = np.nan*np.zeros([6*num_bodies,6*num_bodies,self.data[i].T.size])
                print 'Warning: body ' + str(i) + ' - The WAMTI .out file specified does not contain infinite frequency added mass coefficients'


            if 'am_zero' in locals():

                self.data[i].am.zero = am_zero[6*i:6+6*i,:]
                # self.data[i].am.zero = self.data[i].am.zero*self.rho

            else:

                self.data[i].am.zero = np.nan*np.zeros([6*num_bodies,6*num_bodies,self.data[i].T.size])
                print 'Warning: body ' + str(i) + ' - The WAMTI .out file specified does not contain zero frequency added mass coefficients'
            

            if 'am_all' in locals():
            
                self.data[i].am.all = am_all[6*i:6+6*i,:,:]
                # self.data[i].am.all = self.data[i].am.all*self.rho
            
            else:

                self.data[i].am.all = np.nan*np.zeros([6*num_bodies,6*num_bodies,self.data[i].T.size])
                print 'Warning: body ' + str(i) + ' - The WAMTI .out file specified does not contain any frequency dependent added mass coefficients'

            
            if 'rd_all' in locals():

                self.data[i].rd.all = rd_all[6*i:6+6*i,:,:]
                # for j in xrange(np.shape(self.data[i].rd.all)[2]):
                    # self.data[i].rd.all[:,:,j] = self.data[i].rd.all[:,:,j]*self.rho*self.data[i].w[j]

            else:

                self.data[i].rd.all = np.nan*np.zeros([6*num_bodies,6*num_bodies,self.data[i].T.size])
                print 'Warning: body ' + str(i) + ' - The WAMTI .out file specified does not contain any frequency dependent radiation damping coefficients'

            if 'ex_all' in locals():

                self.data[i].ex.mag = ex_all[6*i:6+6*i,:,:]#*self.rho*self.g
                self.data[i].ex.phase = np.deg2rad(phase_all[6*i:6+6*i,:,:])
                self.data[i].ex.re = self.data[i].ex.mag*np.cos(self.data[i].ex.phase)
                self.data[i].ex.im = self.data[i].ex.mag*np.sin(self.data[i].ex.phase)

            else:

                print 'Warning: body ' + str(i) + ' - The WAMTI .out file specified does not contain any excitation coefficients'


            if 'rao_all' in locals():

                self.data[i].rao.mag = rao_all[6*i:6+6*i,:,:]
                self.data[i].rao.phase = np.deg2rad(phase_all[6*i:6+6*i,:,:])
                self.data[i].rao.re = self.data[i].rao.mag*np.cos(self.data[i].rao.phase)
                self.data[i].rao.im = self.data[i].rao.mag*np.sin(self.data[i].rao.phase)

            else:

                print 'Warning: body ' + str(i) + ' - The WAMTI .out file specified does not contain any rao data'

            if 'ssy_all' in locals():

                self.data[i].ssy.mag = ssy_all[6*i:6+6*i,:,:]
                self.data[i].ssy.phase = np.deg2rad(phase_all[6*i:6+6*i,:,:])
                self.data[i].ssy.re = self.data[i].ssy.mag*np.cos(self.data[i].ssy.phase)
                self.data[i].ssy.im = self.data[i].ssy.mag*np.sin(self.data[i].ssy.phase)

            else:

                print 'Warning: body ' + str(i) + ' - The WAMTI .out file specified does not contain any rao data'


            self.data[i].bem_raw_data = raw
            self.data[i].bem_code = code

        # print 'Dimensionalized WAMIT Hydrodynamic coefficients with g = ' + str(self.g) + ' and rho = ' + str(self.rho)
        print 'Successfully read WAMIT coefficients' 
