import axios from "axios";
import {
  Textbook,
  Chapter,
  PaperData,
  PaperSummary,
  BlueprintValidationResult,
  AnswerKeyData
} from "../types";

// Read backend base URL from environment variable (for production deployment on Vercel)
const RAW_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "";
export const API_BASE_URL = RAW_API_BASE_URL.replace(/\/+$/, "");

const api = axios.create({
  baseURL: API_BASE_URL ? `${API_BASE_URL}/api` : "/api"
});

export const textbookService = {
  async getAll(): Promise<Textbook[]> {
    const res = await api.get<Textbook[]>("/textbooks");
    return res.data;
  },

  async getById(id: number): Promise<Textbook> {
    const res = await api.get<Textbook>(`/textbooks/${id}`);
    return res.data;
  },

  async upload(formData: FormData, onProgress?: (pct: number) => void): Promise<Textbook> {
    const res = await api.post<Textbook>("/textbooks/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      }
    });
    return res.data;
  },

  async updateChapters(id: number, chapters: Partial<Chapter>[]): Promise<Chapter[]> {
    const res = await api.put<Chapter[]>(`/textbooks/${id}/chapters`, chapters);
    return res.data;
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/textbooks/${id}`);
  }
};

export const blueprintService = {
  async getBlueprints(grade: string) {
    const res = await api.get(`/blueprints?grade=${grade}`);
    return res.data;
  },

  async validate(total_marks: number, sections: any[]): Promise<BlueprintValidationResult> {
    const res = await api.post<BlueprintValidationResult>("/blueprints/validate", {
      total_marks,
      sections
    });
    return res.data;
  },

  async saveCustom(data: any) {
    const res = await api.post("/blueprints", data);
    return res.data;
  }
};

export const paperService = {
  async getAll(): Promise<PaperSummary[]> {
    const res = await api.get<PaperSummary[]>("/papers");
    return res.data;
  },

  async getById(id: number) {
    const res = await api.get(`/papers/${id}`);
    return res.data;
  },

  async generate(payload: any) {
    const res = await api.post("/papers/generate", payload);
    return res.data;
  },

  async update(id: number, paperData: PaperData, validateMarks = true) {
    const res = await api.put(`/papers/${id}`, {
      paper_data: paperData,
      validate_marks: validateMarks
    });
    return res.data;
  },

  async regenerateQuestion(id: number, sectionIndex: number, questionIndex: number) {
    const res = await api.post(`/papers/${id}/regenerate-question`, {
      section_index: sectionIndex,
      question_index: questionIndex
    });
    return res.data;
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/papers/${id}`);
  },

  async getAnswerKey(id: number): Promise<AnswerKeyData> {
    const res = await api.get<AnswerKeyData>(`/papers/${id}/answer-key`);
    return res.data;
  },

  getRenderUrl(id: number): string {
    return `${API_BASE_URL}/api/papers/${id}/render`;
  },

  /**
   * Downloads A4 PDF using a real POST request, reads as Blob, and triggers browser download.
   */
  async downloadPdf(id: number, customFilename?: string): Promise<void> {
    const url = `${API_BASE_URL}/api/papers/${id}/export/pdf`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMsg = `PDF Export failed: ${response.status} ${response.statusText}`;
      try {
        const json = JSON.parse(errorText);
        if (json.detail) errorMsg = json.detail;
      } catch {
        if (errorText) errorMsg = errorText;
      }
      throw new Error(errorMsg);
    }

    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      const json = await response.json();
      throw new Error(json.detail || "Server returned an error instead of a PDF file.");
    }

    const blob = await response.blob();
    const filename = customFilename || `hindi-paper-${id}.pdf`;
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },

  /**
   * Downloads Word DOCX using a real POST request with include_answer_key, reads as Blob, and triggers browser download.
   */
  async downloadDocx(id: number, includeAnswerKey = false, customFilename?: string): Promise<void> {
    const url = `${API_BASE_URL}/api/papers/${id}/export/word?include_answer_key=${includeAnswerKey}`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        include_answer_key: includeAnswerKey
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMsg = `Word DOCX Export failed: ${response.status} ${response.statusText}`;
      try {
        const json = JSON.parse(errorText);
        if (json.detail) errorMsg = json.detail;
      } catch {
        if (errorText) errorMsg = errorText;
      }
      throw new Error(errorMsg);
    }

    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      const json = await response.json();
      throw new Error(json.detail || "Server returned an error instead of a Word document.");
    }

    const blob = await response.blob();
    const filename = customFilename || `hindi-paper-${id}.docx`;
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  }
};

export default api;
