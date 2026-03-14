import api from "./axios";
import { ENDPOINTS } from "./endpoints";

/**
 * @typedef {{
 *   purchase_id: string,
 *   note_id: string,
 *   title: string,
 *   subject: string,
 *   unit: number | null,
 *   semester: number | null,
 *   dept: string,
 *   description: string,
 *   is_paid: boolean,
 *   price: number,
 *   unlocked_type: string,
 *   unlocked_at: number
 * }} LibraryRecord
 */

/**
 * @typedef {{
 *   note_id: string,
 *   content: string,
 *   cursor: number,
 *   updated_at?: number,
 *   source?: string
 * }} NoteAnnotation
 */

/**
 * @returns {Promise<LibraryRecord[]>}
 */
export async function getMyLibrary() {
  const res = await api.get(ENDPOINTS.library.mine);
  return res.data || [];
}

/**
 * @param {string} noteId
 * @returns {Promise<NoteAnnotation>}
 */
export async function getMyAnnotation(noteId) {
  const res = await api.get(ENDPOINTS.notes.annotations(noteId));
  return res.data;
}

/**
 * @param {string} noteId
 * @param {{content: string, cursor?: number, source?: string}} payload
 * @returns {Promise<NoteAnnotation>}
 */
export async function upsertMyAnnotation(noteId, payload) {
  const res = await api.put(ENDPOINTS.notes.annotations(noteId), {
    content: payload.content,
    cursor: payload.cursor || 0,
    source: payload.source || "web",
  });
  return res.data;
}

/**
 * @param {string} noteId
 * @returns {Promise<{note_id:string, summary:string, topics:string[], key_points:string[], flashcards:Array, quiz:Array}>}
 */
export async function getSmartStudyPack(noteId) {
  const res = await api.get(ENDPOINTS.notes.smartStudyPack(noteId));
  return res.data;
}
