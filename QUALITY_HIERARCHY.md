# Quality Hierarchy System - Feature Documentation

## 🎯 Overview

The **Quality Hierarchy System** is a sophisticated video quality comparison system that prevents accidental replacement of high-quality videos with lower-quality versions. It intelligently analyzes filenames to detect video source, codec, audio quality, resolution, and HDR features.

## ✨ Key Features

### 1. **Smart Quality Detection**
Automatically extracts quality indicators from filenames:
- **Video Source**: BluRay, WEB-DL, WEBRip, HDCam, CAM, etc.
- **Video Codec**: H.265/HEVC, H.264/AVC, AV1, VP9, etc.
- **Audio Quality**: Atmos, TrueHD, DTS-HD, DD5.1, AAC 2.0, etc.
- **Resolution**: 4K/2160p, 1080p, 720p, 480p, etc.
- **HDR**: HDR10+, HDR10, Dolby Vision, etc.
- **Bitrate Bonus**: 10-bit encoding gets bonus points

### 2. **Quality Scoring System**
Each quality indicator has a numerical score:

| Category | Best Examples | Score |
|----------|--------------|-------|
| **Source** | BluRay, UHD | 100 |
| | WEB-DL | 85 |
| | WEBRip | 75 |
| | HDCam, CAM | 15-25 |
| **Codec** | H.265/HEVC | 20 |
| | H.264/AVC | 15 |
| **Audio** | Atmos, TrueHD | 95-100 |
| | DD5.1 | 80 |
| | AAC 2.0 | 50 |
| **Resolution** | 4K/2160p | 100 |
| | 1080p | 70 |
| | 720p | 50 |
| **HDR** | Dolby Vision | 18 |
| | HDR10+ | 15 |
| | HDR10 | 12 |

### 3. **Replacement Logic**
The system uses these rules to decide whether to replace existing files:

#### Rule 1: Better Quality → Replace ✅
```
Existing: Movie.2023.1080p.HDCam.AAC.mkv (Score: 145)
New:      Movie.2023.1080p.BluRay.DD5.1.mkv (Score: 250)
Decision: REPLACE ✅ (Better quality)
```

#### Rule 2: Same Quality, Smaller Size → Replace ✅
```
Existing: Movie.2023.1080p.BluRay.x264.DD5.1.mkv (3.5GB)
New:      Movie.2023.1080p.BluRay.x265.DD5.1.mkv (2.1GB)
Decision: REPLACE ✅ (Same quality, smaller file - saves 1.4GB)
```

#### Rule 3: Lower Quality → Skip ❌
```
Existing: Movie.2023.1080p.BluRay.DD5.1.mkv (Score: 250)
New:      Movie.2023.1080p.HDCam.AAC.mkv (Score: 145)
Decision: SKIP ❌ (Lower quality - protects existing BluRay)
```

#### Rule 4: Different Resolutions → Use Default Logic
```
Existing: Movie.2023.720p.BluRay.mkv
New:      Movie.2023.1080p.HDCam.mkv
Decision: Uses original replacement logic (resolution mismatch)
```

## 🔧 Technical Implementation

### File Structure
```
Backend/helper/quality_checker.py     # Core quality comparison logic
Backend/helper/database.py            # Updated with quality checks
Backend/tests/test_quality_checker.py # Comprehensive test suite
test_quality_standalone.py            # Standalone testing script
```

### Integration Points

#### In `database.py` - Movie Updates
```python
# Before (Old Logic)
if matching_quality:
    matching_quality.update(quality_to_update)  # Always replaces

# After (Quality Hierarchy)
if matching_quality:
    should_replace, reason = QualityChecker.should_replace_quality(
        existing_quality_label=matching_quality.get("quality", ""),
        existing_quality_name=matching_quality.get("name", ""),
        existing_quality_size=matching_quality.get("size", ""),
        new_quality_label=quality_to_update.get("quality", ""),
        new_quality_name=quality_to_update.get("name", ""),
        new_quality_size=quality_to_update.get("size", "")
    )
    
    if should_replace:
        LOGGER.info(f"Quality replacement approved: {reason}")
        # Delete old file and update
    else:
        LOGGER.warning(f"Quality replacement blocked: {reason}")
        return movie_id  # Skip replacement
```

#### In `database.py` - TV Show Updates
Same logic applies to TV show episodes with matching quality labels.

## 📊 Quality Rankings Reference

### Video Source Rankings (Higher = Better)

| Rank | Source Type | Score | Description |
|------|-------------|-------|-------------|
| 🥇 | BluRay, UHD, 4K | 100 | Best quality, direct from disc |
| 🥈 | WEB-DL | 85 | Downloaded from streaming, untouched |
| 🥉 | WEBRip | 75 | Ripped from streaming |
| 📀 | DVDRip | 60 | Ripped from DVD |
| 📺 | HDTV, DSNP, NF | 50-70 | TV/streaming recordings |
| 📹 | DVDScr, R5 | 35-40 | Screeners, preview copies |
| 📷 | HDCam, Cam | 15-25 | Camera recordings (poor) |

### Audio Quality Rankings

| Rank | Audio Format | Score | Channels |
|------|-------------|-------|----------|
| 🔊 | Atmos, TrueHD | 95-100 | Object-based audio |
| 🔉 | DTS-HD MA | 95 | Lossless 5.1/7.1 |
| 🔉 | DD5.1, AC3 | 80 | Standard 5.1 surround |
| 🔈 | AAC 2.0 | 50 | Stereo |

### Video Codec Rankings

| Codec | Score | Notes |
|-------|-------|-------|
| H.265/HEVC | 20 | Best compression, smaller files |
| AV1 | 18 | Modern, excellent compression |
| H.264/AVC | 15 | Standard codec |
| VP9 | 12 | Google codec |

## 📝 Log Output Examples

### Scenario 1: Quality Downgrade Prevented ❌
```
[INFO] Quality Comparison:
  Existing: Avengers.Endgame.2019.1080p.BluRay.DD5.1.x265.10bit.mkv
    Score: 275 (source:100, codec:20, audio:80, res:70, hdr:0)
    Size: 3.0GB (3072.00 MB)
  New: Avengers.Endgame.2019.1080p.HDCam.AAC.2.0.mkv
    Score: 145 (source:25, codec:0, audio:50, res:70, hdr:0)
    Size: 2.1GB (2150.40 MB)
  Decision: ❌ SKIP - Lower quality detected! (score: 145 < 275)
[WARNING] Quality replacement blocked: Lower quality detected!
```

### Scenario 2: Quality Upgrade Approved ✅
```
[INFO] Quality Comparison:
  Existing: Movie.2023.1080p.HDCam.AAC.mkv
    Score: 145 (source:25, codec:0, audio:50, res:70, hdr:0)
    Size: 1.5GB (1536.00 MB)
  New: Movie.2023.1080p.BluRay.DD5.1.mkv
    Score: 250 (source:100, codec:0, audio:80, res:70, hdr:0)
    Size: 3.2GB (3276.80 MB)
  Decision: ✅ REPLACE - Better quality (score: 250 > 145)
[INFO] Quality replacement approved: Better quality
[INFO] Deleted message 407 in -1003261695898
```

### Scenario 3: Size Optimization ✅
```
[INFO] Quality Comparison:
  Existing: Movie.2023.1080p.BluRay.x264.DD5.1.mkv
    Score: 265 (source:100, codec:15, audio:80, res:70, hdr:0)
    Size: 3.5GB (3584.00 MB)
  New: Movie.2023.1080p.BluRay.x265.HEVC.DD5.1.mkv
    Score: 270 (source:100, codec:20, audio:80, res:70, hdr:0)
    Size: 2.1GB (2150.40 MB)
  Decision: ✅ REPLACE - Better quality (score: 270 > 265)
[INFO] Quality replacement approved: Better codec, smaller size
```

## 🧪 Testing

### Run Standalone Tests
```bash
cd "e:\New folder (5)\telgram-stremio-modifiyed"
python test_quality_standalone.py
```

### Run Full Test Suite (requires dependencies)
```bash
uv run python -m pytest Backend/tests/test_quality_checker.py -v
```

### Test Coverage
- ✅ BluRay vs HDCam protection
- ✅ Quality upgrade scenarios
- ✅ Same quality with size preference (HEVC)
- ✅ WEB-DL vs WEBRip comparison
- ✅ Audio quality preservation (DD5.1 vs AAC)
- ✅ HDR bonus scoring
- ✅ 10-bit encoding bonus
- ✅ Different resolution fallback
- ✅ Complex filename parsing
- ✅ File size parsing (GB, MB, KB)
- ✅ Real-world torrent scenarios

## 🚀 Deployment

### Git Branch: `quality-hierarchy`
```bash
git checkout quality-hierarchy
git status
```

### Files Modified
1. `Backend/helper/quality_checker.py` - New quality comparison engine
2. `Backend/helper/database.py` - Integrated quality checks in update_movie() and update_tv_show()

### Files Added
3. `Backend/tests/test_quality_checker.py` - Comprehensive test suite
4. `test_quality_standalone.py` - Standalone testing script
5. `QUALITY_HIERARCHY.md` - This documentation

## 📚 Usage Examples

### Example 1: Protecting High-Quality Files
```
User forwards: Movie.2023.1080p.BluRay.DD5.1.mkv → Stored ✅
User forwards: Movie.2023.1080p.HDCam.AAC.mkv → Blocked ❌
Result: BluRay version protected
```

### Example 2: Optimizing Storage
```
User forwards: Movie.2023.1080p.BluRay.x264.3.5GB → Stored ✅
User forwards: Movie.2023.1080p.BluRay.HEVC.2.1GB → Replaces ✅
Result: Same quality, saves 1.4GB storage
```

### Example 3: Quality Upgrades
```
User forwards: Movie.2023.1080p.HDCam.mkv → Stored ✅
User forwards: Movie.2023.1080p.WEBRip.mkv → Replaces ✅
User forwards: Movie.2023.1080p.WEB-DL.mkv → Replaces ✅
User forwards: Movie.2023.1080p.BluRay.mkv → Replaces ✅
Result: Progressive quality improvements
```

## ⚠️ Important Notes

### Backward Compatibility
- ✅ **Different resolutions** (720p vs 1080p) use original replacement logic
- ✅ **Same resolution** (1080p vs 1080p) uses Quality Hierarchy System
- ✅ Existing behavior preserved for resolution mismatches

### Edge Cases Handled
- Unknown quality indicators → Uses available scores
- Missing file sizes → Allows replacement based on quality alone
- Complex filenames → Parses multiple quality indicators
- Multi-word audio formats (e.g., "DD 5.1", "DD5.1") → Both recognized

### Known Limitations
- Requires quality indicators in filename (BluRay, x265, DD5.1, etc.)
- Cannot detect quality from video inspection (filename-based only)
- Assumes proper naming conventions (PTN-compatible)

## 🔮 Future Enhancements

### Potential Improvements
1. **Manual Quality Override**: `/force` command to bypass quality checks
2. **Quality Notifications**: Bot messages when quality downgrades are blocked
3. **Quality Statistics**: Dashboard showing quality distribution
4. **Custom Rankings**: Admin-configurable quality preferences
5. **Video Analysis**: FFprobe integration for codec/audio verification

## 📞 Support

### Debugging Quality Issues
1. Check `log.txt` for quality comparison details
2. Look for "Quality Comparison:" log entries
3. Review score breakdowns for each file
4. Verify filename contains quality indicators

### Common Issues
- **Replacement still happening**: Check if resolutions differ (720p vs 1080p)
- **Files not replacing**: Check if new quality score is lower
- **Size comparison not working**: Verify size format in database (e.g., "2.5GB")

---

**Version**: 1.0.0  
**Branch**: `quality-hierarchy`  
**Author**: Expert Implementation  
**Date**: November 2025
