export interface Chapter {
  id?: number;
  unit_name: string;
  chapter_number: number;
  title: string;
  author: string;
  chapter_type: "prose" | "poetry" | "supplementary" | "grammar" | "writing";
  start_page: number;
  end_page: number;
  extracted_text?: string;
}

export interface Textbook {
  id: number;
  title: string;
  grade: string;
  book_name: string;
  filename: string;
  file_size: number;
  total_pages: number;
  extracted_pages: number;
  scanned_pages: number;
  low_text_pages: number;
  ocr_warning: boolean;
  status: string;
  error_message?: string;
  created_at: string;
  chapters: Chapter[];
}

export interface SubQuestion {
  id?: string;
  sub_number: string;
  sub_text: string;
  marks: number;
  items: string[];
  answer?: string;
}

export interface QuestionItem {
  id?: string;
  question_number: string;
  question_text: string;
  marks: number;
  source_type: "textbook" | "ai_generated" | "teacher_created";
  chapter: string;
  source_page?: string;
  source_confidence?: "high" | "medium" | "low";
  answer?: string;
  passage?: string;
  is_poem?: boolean;
  sub_questions?: SubQuestion[];
}

export interface SectionItem {
  section_number: number;
  section_title: string;
  section_marks: number;
  questions: QuestionItem[];
}

export interface PaperMetadata {
  class: string;
  class_name?: string;
  subject: string;
  book: string;
  exam_type: string;
  duration: string;
  total_marks: number;
  difficulty: string;
  school_name: string;
  tagline: string;
  exam_title: string;
  academic_year?: string;
  exam_date?: string;
  teacher_name?: string;
  has_logo?: boolean;
}

export interface PaperData {
  metadata: PaperMetadata;
  general_instructions?: string[];
  sections: SectionItem[];
  total_marks: number;
  warnings?: string[];
}

export interface PaperSummary {
  id: number;
  title: string;
  grade: string;
  subject: string;
  exam_type: string;
  duration: string;
  total_marks: number;
  school_name: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface BlueprintValidationResult {
  is_valid: boolean;
  configured_total: number;
  calculated_total: number;
  difference: number;
  errors: string[];
  warnings: string[];
}

export interface AnswerKeyItem {
  section_title: string;
  question_number: string;
  question_text: string;
  expected_answer: string;
  marks: number;
  points: string[];
  teacher_verification_required: boolean;
}

export interface AnswerKeyData {
  exam_title: string;
  total_marks: number;
  answers: AnswerKeyItem[];
  notes?: string;
}

export interface UploadedPaper {
  id: number;
  title: string;
  grade: string;
  subject: string;
  original_filename: string;
  file_type: "pdf" | "docx" | "image";
  file_size: number;
  has_pdf: boolean;
  has_docx: boolean;
  conversion_status: string;
  conversion_warning: string;
  created_at: string;
}
