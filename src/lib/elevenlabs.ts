const API_KEY = import.meta.env.VITE_ELEVENLABS_API_KEY;
const VOICE_ID = import.meta.env.VITE_ELEVENLABS_VOICE_ID;

let currentAudio: HTMLAudioElement | null = null;

export async function speak(text: string): Promise<void> {
  if (!API_KEY || !VOICE_ID) {
    console.warn('ElevenLabs not configured — skipping TTS');
    return;
  }

  // Stop any currently playing audio
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }

  const response = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}`,
    {
      method: 'POST',
      headers: {
        'xi-api-key': API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        model_id: 'eleven_turbo_v2_5',
        voice_settings: {
          stability: 0.5,
          similarity_boost: 0.75,
          style: 0.3,
        },
      }),
    }
  );

  if (!response.ok) {
    console.error('ElevenLabs TTS failed:', response.status);
    return;
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  currentAudio = new Audio(url);
  await currentAudio.play();

  return new Promise((resolve) => {
    currentAudio!.onended = () => {
      URL.revokeObjectURL(url);
      currentAudio = null;
      resolve();
    };
  });
}

export function stopSpeaking() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
}
