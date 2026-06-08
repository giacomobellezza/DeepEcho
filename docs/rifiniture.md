SUGGERIMENTI:

Performance / Bugs: 

    Loading failed after max 2 dives (~2h). 
    Light mode doesn’t work. It might be useful in the future for downloading images with white background for presentations. 


User Experience: 

    Not very clear that you need to click on Browse file before clicking on Upload Files. 
    Idea: Set Browse File blue, then switch to grey once file has been selected and Upload Files always gray until all files have been browsed and are ready to be uploaded.
    Not a big deal anyway, this is just a note.

    Time interval selection (at the bottom of the page) could be more evident since it’s one of the main tools we constantly interact with to visualize portions of the data. 
    Would it be feasible to add a “minutes” drop-down menu instead of only seconds? Maybe more handy.

    In 3D trajectory we could activate/deactivate the displaying of acoustic events like creaks, regular_clicks, coda, etc. (Right now there is the prey capture calculated with the jerk) 
    & it could be useful to visualize local time, either by uploading a dedicated file with that info, or by inserting it manually (e.g. DP2 start time 14:05:06.860)

    Time Resolution in section Events: 
    show acoustic events duration as SS.FF instead of S (04.12s vs 4s) 
    & can we have the timestamp of each event on the same line as the duration so that we know if they are subsequent or not when filtering by type? e.g. 
    coda_121    14:07:11     1.3s
    creak             14:10:00    15.3s


Visualization:

    Fix  Spectrogram Parameters (1024 FFT, overlap 50% ok, if possible adjustable signal amplitude scale (dB) for better contrast, but we can discuss it)
    Fix PRH +/- 180° visual jump
    Whale marker on 3D trajectory more visible / contrasted / bigger ?

Next Steps/Ideas:

    Load GPS file to be visualized on a map showing location and bathymetry 

    Create a processed file to be locally dowloaded and then uploaded just to be visualized instead of calculating it each time

    Remove Prey capture with jerk (not sure yet if it's applicable to our data)

    Can we “press Play” and see the trajectory moving? Maybe with the option of downloading the GIF or video and pair it with other panels like my MATLAB script?

    Can we select multiple subsequent events and visualize them instead of just one at the time?  

    I would add some parameters in the “Statistics” panel that I can share in a separate document 


    As for the dive phases, we can work on the automatization following certain parameters but for now we could either: 
    1. Load a file with the relative timestamps of each phase start and end 
    2. Select them manually on a 2D zoomable diving profile. Like a UI that asks the user to select start & end of each dive phase:
    Surface
    Descent
    Foraging 
    Bottom
    Ascent


 Performance / Bugs: 

    Loading failed after max 2 dives (~2h). 
    Light mode doesn’t work. It might be useful in the future for downloading images with white background for presentations. 


User Experience: 

    Not very clear that you need to click on Browse file before clicking on Upload Files. 
    Idea: Set Browse File blue, then switch to grey once file has been selected and Upload Files always gray until all files have been browsed and are ready to be uploaded.
    Not a big deal anyway, this is just a note.

    Time interval selection (at the bottom of the page) could be more evident since it’s one of the main tools we constantly interact with to visualize portions of the data. 
    Would it be feasible to add a “minutes” drop-down menu instead of only seconds? Maybe more handy.

    In 3D trajectory we could activate/deactivate the displaying of acoustic events like creaks, regular_clicks, coda, etc. (Right now there is the prey capture calculated with the jerk) 
    & it could be useful to visualize local time, either by uploading a dedicated file with that info, or by inserting it manually (e.g. DP2 start time 14:05:06.860)

    Time Resolution in section Events: 
    show acoustic events duration as SS.FF instead of S (04.12s vs 4s) 
    & can we have the timestamp of each event on the same line as the duration so that we know if they are subsequent or not when filtering by type? e.g. 
    coda_121    14:07:11     1.3s
    creak             14:10:00    15.3s


Visualization:

    Fix  Spectrogram Parameters (1024 FFT, overlap 50% ok, if possible adjustable signal amplitude scale (dB) for better contrast, but we can discuss it)
    Fix PRH +/- 180° visual jump
    Whale marker on 3D trajectory more visible / contrasted / bigger ?

Next Steps/Ideas:

    Load GPS file to be visualized on a map showing location and bathymetry 

    Create a processed file to be locally dowloaded and then uploaded just to be visualized instead of calculating it each time

    Remove Prey capture with jerk (not sure yet if it's applicable to our data)

    Can we “press Play” and see the trajectory moving? Maybe with the option of downloading the GIF or video and pair it with other panels like my MATLAB script?

    Can we select multiple subsequent events and visualize them instead of just one at the time?  

    I would add some parameters in the “Statistics” panel that I can share in a separate document 


    As for the dive phases, we can work on the automatization following certain parameters but for now we could either: 
    1. Load a file with the relative timestamps of each phase start and end 
    2. Select them manually on a 2D zoomable diving profile. Like a UI that asks the user to select start & end of each dive phase:
    Surface
    Descent
    Foraging 
    Bottom
    Ascent

---

Come ci siamo detti durante la call, nelle prossime iterazioni lavoreremo sicuramente su alcuni punti prioritari:

    aggiunta della light mode

    miglioramento della visualizzazione dello spettrogramma, con maggiore enfasi sui dB e una color scale più efficace

    fix relativi ai timestamp

    possibilità di visualizzare il tempo in secondi / minuti / ore oppure direttamente come timestamp assoluto


Per quanto riguarda invece la struttura di upload, penso che una soluzione molto pulita possa essere quella di caricare direttamente una cartella contenente tutti i file necessari al deployment, ad esempio:

    file audio

    file di locomotion

    file eventi

    file JSON con i metadati del deployment

Gli eventi potrebbero eventualmente essere anche calcolati automaticamente dalla piattaforma; magari questo può diventare il focus di una prossima discussione dedicata.

Immagino qualcosa di questo tipo per il file JSON dei metadati:

{
  "title": "Sperm whale deployment - DP2",
  "animal_id": "SW_001",
  "species": "Physeter macrocephalus",

  "deployment_start": "2026-05-28T14:05:06.860Z",
  "deployment_end": "2026-05-28T18:42:10.120Z",

  "timezone": "UTC+2",

  "gps_track": [
    {
      "timestamp": "2026-05-28T14:10:00.000Z",
      "latitude": 43.12345,
      "longitude": 10.54321
    },
    {
      "timestamp": "2026-05-28T14:15:00.000Z",
      "latitude": 43.12410,
      "longitude": 10.54402
    }
  ],

  "research_group": "Project Name / Institution",
  "notes": "Optional deployment notes",

  "additional_metadata": {
    "tag_model": "DTAG-X",
    "sampling_rate_audio": 192000,
    "sampling_rate_sensors": 400
  }
}


---

 Ottima pipeline di upload. Si, dovremo lavorare sulla flessibilità di questi file se vogliamo rendere il progetto condivisibile. Il PRH.mat, se processato tramite lo script MATLAB di Standford, sarà pressoché uguale per tutti, gli altri file no, quindi dobbiamo riflettere su questa cosa. 

Perfetto per il file JSON, ho preparato un primo file (DP1) in cui ho riporto alcune informazioni principali in modo tale che tu possa fare una prova appena avrai modo, e con calma proviamo a risentirci nelle prossime settimane.

--- GENERAL INFO ---
Deployment ID:    pm20240701-CD3
Species:          Physeter macrocephalus
Project:	  DIVES \ SZN
Notes:            Photogrammetry\Biopsy\Blow

--- DATE ---
Deployment Start: 2024-07-01 13:02:00.820 (YY:MM:DD HH:SS:MM.FFF)
Deployment End:   2024-07-01 21:21:48.620
Timezone:         UTC+2

--- GPS TRACK LOG --- Timestamp in Local Time
Point 1: (Tag On) 
  Timestamp: 13:03:01.000	
  Latitude:  37.1118
  Longitude: 15.3438
Point 2: (Surface 1) 
  Timestamp: 13:55:43.000
  Latitude:  37.1228
  Longitude: 15.3351
Point 3: (Surface 2) 
  Timestamp: 14:33:42.780
  Latitude:  37.1498
  Longitude: 15.3369
Point 4: (Surface 3) 
  Timestamp: 15:15:15.770
  Latitude:  37.1449
  Longitude: 15.3406
Point 5: (Surface 4) 
  Timestamp: 16:05:58.820
  Latitude:  37.1841
  Longitude: 15.3413
Point 6: (Surface 5) 
  Timestamp: 16:45:13.810
  Latitude:  37.1960
  Longitude: 15.3334
Point 7: (Surface 6) 
  Timestamp: 17:35:41.900
  Latitude:  37.2126
  Longitude: 15.3480
Point 8: (Surface 7) 
  Timestamp: 18:15:41.780
  Latitude:  37.2027
  Longitude: 15.3486
Point 9: (Tag Recovery) 
  Timestamp: 23:32:42.820
  Latitude:  37.2790
  Longitude: 15.3284

--- ADDITIONAL METADATA ---
Tag Model:            CATS Diary CD3
Sampling Rate Audio:  192000 Hz
Sampling Rate Sensors:400 Hz
==================================================
---


queste sono le mail dove pianifichiamo il prossimo sviluppo.