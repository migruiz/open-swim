

#TODO: Sync  files to this folder sd_card_path = os.getenv("OPEN_SWIM_SD_PATH", "/sdcard") / podcast
#the folder already exists no need to check
# create a pydantic class PodcastEpisode for this json
# {
#    "id": "692726a2eafa3981bcda3d0b",
#    "date": "2025-11-26 16:02:51+00:00",
#    "download_url": "https://dts.podtrac.com/redirect.mp3/od-cmg.streamguys1.com/sanantonio/san995/20251126100250-38-BillyMadisonShowPodcast-November262025.mp3?awCollectionId=san995-02&awGenre=Comedy&awEpisodeId=5c56a100-cae1-11f0-99fd-9d2893fba4d7",
#    "title": "Billy Madison Show Podcast - November, 26, 2025"
#  }
# check that the /sdcard/podcast folder contains a synced_episodes.json file which is a list of the above objects
# now read the episodes to sync from this location 
# LIBRARY_PATH = os.getenv('LIBRARY_PATH', '/library')
#podcasts_library_path = os.path.join(LIBRARY_PATH, "podcasts") / episodes_to_sync.json

# now check if the episdes ids are the same in both files, if they are the same do nothing
# if they are different DELETE all files from the /sdcard/podcast folder
#now read the contents of the library os.path.join(LIBRARY_PATH, "podcasts") / info.json
#which are in this format:
{
  "episodes": {
    "692726a2eafa3981bcda3d0b": {
      "id": "692726a2eafa3981bcda3d0b",
      "title": "Billy Madison Show Podcast - November, 26, 2025",
      "date": "2025-11-26T16:02:51Z",
      "episode_dir": "C:\\Users\\miguelpc\\Music\\OpenSwimLibrary\\podcasts\\Billy_Madison_Show_Podcast_-_November_26_2025_692726a2eafa3981bcda3d0b"
    },
    "6925d4487fe9472599152092": {
      "id": "6925d4487fe9472599152092",
      "title": "Billy Madison Show Podcast - November, 25, 2025",
      "date": "2025-11-25T16:00:31Z",
      "episode_dir": "C:\\Users\\miguelpc\\Music\\OpenSwimLibrary\\podcasts\\Billy_Madison_Show_Podcast_-_November_25_2025_6925d4487fe9472599152092"
    }
  }
}

# now search any episode id in the podcast_to_sync.json file in the library info.json file, get the episode_dir and copy 
#all mp3 files from there to the /sdcard/podcast folder
#finally save the podcast_to_sync.json file to the /sdcard/podcast/synced_episodes.json file
