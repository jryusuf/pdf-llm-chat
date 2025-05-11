from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from app.pdf.domain.models import PDFDocument, PDFParseStatus
from app.pdf.infrastucture.repositories.pdf_repository import IPDFRepository
from app.pdf.domain.exceptions import PDFNotFoundError
import io
from typing import Optional, Any, List
from datetime import datetime, timezone


class MongoPDFRepository(IPDFRepository):
    def __init__(self, db: AsyncIOMotorDatabase, fs: Optional[AsyncIOMotorGridFSBucket] = None):
        self.db = db
        self.pdf_meta_collection = db["pdf_metadata_collection"]
        self.parsed_texts_collection = db["parsed_pdf_texts_collection"]
        self.fs = fs if fs else AsyncIOMotorGridFSBucket(db, bucket_name="pdf_binaries")

    async def _doc_to_domain(self, doc: dict) -> Optional[PDFDocument]:
        if not doc:
            return None
        return PDFDocument(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            gridfs_file_id=str(doc["gridfs_file_id"]),
            original_filename=doc["original_filename"],
            upload_date=doc.get("upload_date"),  # Allow for missing if schema evolves
            parse_status=PDFParseStatus(doc.get("parse_status", "UNPARSED")),
            parse_error_message=doc.get("parse_error_message"),
            is_selected_for_chat=doc.get("is_selected_for_chat", False),
            parsed_text_id=str(doc["parsed_text_id"]) if doc.get("parsed_text_id") else None,
        )

    async def save_pdf_binary(
        self, filename: str, content: bytes, user_id: int, content_type: str = "application/pdf"
    ) -> str:
        gridfs_id = await self.fs.upload_from_stream(
            filename,
            io.BytesIO(content),  # GridFS expects a stream-like object
            metadata={"contentType": content_type, "user_id": user_id},
        )
        return str(gridfs_id)

    async def save_pdf_meta(self, pdf_doc: PDFDocument) -> PDFDocument:
        # MongoDB generates _id, so we don't pass pdf_doc.id directly for insert
        # But if pdf_doc.id was pre-generated (e.g. UUID string), we could use it as _id.
        # For this example, assume Mongo generates ObjectId.
        meta_doc = {
            "user_id": pdf_doc.user_id,
            "gridfs_file_id": ObjectId(pdf_doc.gridfs_file_id),
            "original_filename": pdf_doc.original_filename,
            "upload_date": pdf_doc.upload_date,
            "parse_status": pdf_doc.parse_status.value,
            "parse_error_message": pdf_doc.parse_error_message,
            "is_selected_for_chat": pdf_doc.is_selected_for_chat,
            "parsed_text_id": ObjectId(pdf_doc.parsed_text_id) if pdf_doc.parsed_text_id else None,
        }
        result = await self.pdf_meta_collection.insert_one(meta_doc)
        pdf_doc.id = str(result.inserted_id)  # Update domain object with generated ID
        return pdf_doc

    async def get_pdf_meta_by_id(self, pdf_id: str, user_id: int) -> Optional[PDFDocument]:
        try:
            obj_id = ObjectId(pdf_id)
        except Exception:
            return None
        doc = await self.pdf_meta_collection.find_one({"_id": obj_id, "user_id": user_id})
        return await self._doc_to_domain(doc)

    async def get_pdf_binary_stream_by_gridfs_id(
        self, gridfs_id: str
    ) -> Optional[AsyncIOMotorGridFSBucket]:  # Actually returns GridOut object for streaming
        try:
            obj_id = ObjectId(gridfs_id)
            grid_out = await self.fs.open_download_stream(obj_id)
            return grid_out  # Caller needs to read() from this
        except Exception:  # e.g. NoFile
            return None

    async def get_all_pdf_meta_for_user(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> List[PDFDocument]:
        cursor = (
            self.pdf_meta_collection.find({"user_id": user_id})
            .sort("upload_date", -1)
            .skip(skip)
            .limit(limit)
        )
        docs_domain = []
        async for doc in cursor:
            domain_obj = await self._doc_to_domain(doc)
            if domain_obj:
                docs_domain.append(domain_obj)
        return docs_domain

    async def count_all_pdf_meta_for_user(self, user_id: int) -> int:
        return await self.pdf_meta_collection.count_documents({"user_id": user_id})

    async def update_pdf_meta(self, pdf_doc: PDFDocument) -> PDFDocument:
        try:
            obj_id = ObjectId(pdf_doc.id)
        except Exception:
            raise PDFNotFoundError(pdf_id=pdf_doc.id)  # Or appropriate error

        update_data = {
            "parse_status": pdf_doc.parse_status.value,
            "parse_error_message": pdf_doc.parse_error_message,
            "is_selected_for_chat": pdf_doc.is_selected_for_chat,
            "parsed_text_id": ObjectId(pdf_doc.parsed_text_id) if pdf_doc.parsed_text_id else None,
            "upload_date": pdf_doc.upload_date,  # Potentially update this too if needed
        }
        result = await self.pdf_meta_collection.update_one(
            {"_id": obj_id, "user_id": pdf_doc.user_id}, {"$set": update_data}
        )
        if result.matched_count == 0:
            raise PDFNotFoundError(pdf_id=pdf_doc.id)  # Or PDFNotOwned if user_id check fails
        return pdf_doc  # Return the updated domain object passed in

    async def set_pdf_selected_for_chat(self, user_id: int, pdf_id_to_select: str) -> bool:
        try:
            select_obj_id = ObjectId(pdf_id_to_select)
        except Exception:
            return False  # Invalid pdf_id format

        # Deselect all others for this user
        await self.pdf_meta_collection.update_many(
            {"user_id": user_id, "is_selected_for_chat": True, "_id": {"$ne": select_obj_id}},
            {"$set": {"is_selected_for_chat": False}},
        )
        # Select the target one
        result = await self.pdf_meta_collection.update_one(
            {"_id": select_obj_id, "user_id": user_id}, {"$set": {"is_selected_for_chat": True}}
        )
        return (
            result.modified_count > 0 or result.matched_count > 0
        )  # True if already selected or newly selected

    async def save_parsed_text(self, pdf_meta_id: str, text_content: str) -> str:
        parsed_text_doc = {
            "pdf_metadata_id": ObjectId(pdf_meta_id),
            "text_content": text_content,
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.parsed_texts_collection.insert_one(parsed_text_doc)
        return str(result.inserted_id)

    async def get_parsed_text_by_pdf_meta_id(self, pdf_meta_id: str) -> Optional[str]:
        try:
            obj_id = ObjectId(pdf_meta_id)
        except Exception:
            return None
        doc = await self.parsed_texts_collection.find_one({"pdf_metadata_id": obj_id})
        return doc["text_content"] if doc else None
