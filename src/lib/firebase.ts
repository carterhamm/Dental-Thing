import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: "AIzaSyCutdI4gjlaol9JgAgYuQulpE--lMH_SsM",
  authDomain: "dentalthing-a5c04.firebaseapp.com",
  projectId: "dentalthing-a5c04",
  storageBucket: "dentalthing-a5c04.firebasestorage.app",
  messagingSenderId: "283851714455",
  appId: "1:283851714455:web:930d7722d26b83f7f99ed2",
  measurementId: "G-1FYGGZR655",
};

const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
