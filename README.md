# Quick Start Guide - Construction Inspection Intelligence App

## 🚀 Getting Started

Your app is now fully enhanced to use all data from the `data/` folder!

### Run the App

```cmd
cd inspection-intelligence
streamlit run app/streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 📊 What You'll See

### Dashboard Tab (Default)
Shows an overview with:
- **4 Metrics**: Total reports (2), PDF pages (5), positive images (20K), negative images (20K)
- **Risk Assessment Table**: All reports analyzed with defects and risk levels
- **Statistics**: Average defects, high-risk count, medium-risk count

### Sample Reports Tab
- Detailed view of all reports from `sample_reports.json`
- Extracted defects for each report
- Risk scores for each

### PDF Documents Tab
- Text extracted from `The_Merged_Approved_Documents_Oct24.pdf`
- First 5 pages analyzed for defects
- Expandable full-text view

### Image Classification Tab
- Statistics on concrete crack dataset
- 20,000+ positive images (with cracks)
- 20,000+ negative images (without cracks)
- Sample images displayed for preview

### Upload Custom Report Tab
- Original feature: Upload your own `.txt` files
- Get instant defect extraction and risk scoring

---

## 📁 Data Source Structure

```
data/
├── sample_reports.json                    ← 2 inspection reports (auto-processed)
├── The_Merged_Approved_Documents_Oct24.pdf ← PDF content (auto-extracted)
└── Concrete Crack Images for Classification/
    ├── Positive/                          ← ~20,000 crack images
    └── Negative/                          ← ~20,000 no-crack images
```

---

## 🔍 Behind the Scenes

**New Module: `pipeline/loader.py`**
- Loads JSON reports automatically
- Extracts PDF text (PyPDF2)
- Counts and retrieves images
- All called from the Streamlit app

**Updated: `app/streamlit_app.py`**
- 5 navigation pages
- Automatic data processing
- Real-time defect extraction
- Risk assessment dashboard

**New Dependencies:**
- `PyPDF2` - PDF text extraction
- `pillow` - Image handling

---

## 💡 Key Features

✅ **Automatic Data Loading** - No manual upload needed  
✅ **Multi-Page Dashboard** - 5 different views  
✅ **Risk Scoring** - Automatic risk assessment  
✅ **PDF Processing** - Extracts text from documents  
✅ **Image Preview** - Sample images from dataset  
✅ **Expandable Details** - Deep dive into any report  
✅ **Statistics Panel** - Aggregate metrics and insights  

---

## 🛠️ Troubleshooting

**Port already in use?**
```cmd
streamlit run app/streamlit_app.py --server.port 8502
```

**Dependencies not installed?**
```cmd
pip install -r requirements.txt
```

**Want to see debug info?**
```cmd
streamlit run app/streamlit_app.py --logger.level=debug
```

---

## 📝 Files Modified/Created

- ✅ **Created**: `pipeline/loader.py` (data loading utilities)
- ✅ **Updated**: `app/streamlit_app.py` (multi-page dashboard)
- ✅ **Updated**: `requirements.txt` (PyPDF2, pillow)
- ✅ **Created**: `UPDATES.md` (comprehensive documentation)

---

**Ready to go!** 🎉

Run `streamlit run app/streamlit_app.py` and explore all your data in one unified dashboard.

