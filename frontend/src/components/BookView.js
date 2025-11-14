import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  AppBar,
  Toolbar,
  IconButton,
} from '@mui/material';
import { ArrowBack, Edit, Check, Close } from '@mui/icons-material';
import axios from 'axios';

function BookView() {
  const { bookId } = useParams();
  const navigate = useNavigate();
  const [segments, setSegments] = useState([]);
  const [book, setBook] = useState(null);
  const [selectedSegment, setSelectedSegment] = useState(null);
  const [overrideDialogOpen, setOverrideDialogOpen] = useState(false);
  const [newTranslation, setNewTranslation] = useState('');
  const [engine, setEngine] = useState('gemini');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBook();
    fetchSegments();
    
    // Auto-refresh segments every 5 seconds to see translation progress
    const interval = setInterval(() => {
      fetchSegments();
    }, 5000);
    
    return () => clearInterval(interval);
  }, [bookId]);

  const fetchBook = async () => {
    try {
      const response = await axios.get(`/api/books/${bookId}`);
      setBook(response.data);
    } catch (error) {
      console.error('Error fetching book:', error);
    }
  };

  const fetchSegments = async () => {
    try {
      const response = await axios.get(`/api/segments/book/${bookId}?page=1&page_size=100&include_metrics=true`);
      setSegments(response.data.segments);
    } catch (error) {
      console.error('Error fetching segments:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTranslateAll = async () => {
    if (!window.confirm('This will translate all pending segments. This may take a while. Continue?')) {
      return;
    }
    
    try {
      // Use sync=false for background, but you can test with sync=true
      const response = await axios.post(`/api/books/${bookId}/translate-all?sync=false`);
      alert(response.data.message || 'Translation started! Check terminal for progress.');
      // Refresh segments periodically
      const refreshInterval = setInterval(() => {
        fetchSegments();
        // Stop refreshing if all segments are translated
        const allTranslated = segments.every(s => s.translated_az || s.status === 'translated');
        if (allTranslated) {
          clearInterval(refreshInterval);
        }
      }, 3000);
    } catch (error) {
      console.error('Error starting translation:', error);
      alert('Error starting translation: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleTranslate = async (segmentId, sourceText) => {
    try {
      const response = await axios.post('/api/translate', {
        source_en: sourceText,
        segment_id: segmentId,
      });
      
      // Update segment in local state
      setSegments((prev) =>
        prev.map((s) =>
          s.id === segmentId
            ? { ...s, translated_az: response.data.translated_az, status: 'translated' }
            : s
        )
      );
    } catch (error) {
      console.error('Error translating:', error);
      alert('Error translating segment');
    }
  };

  const handleRetranslate = async (segmentId, sourceText) => {
    try {
      const response = await axios.post('/api/translate/retranslate', {
        segment_id: segmentId,
        engine: engine,
        source_text: sourceText,
      });
      
      setNewTranslation(response.data.new_translation);
    } catch (error) {
      console.error('Error retranslating:', error);
      alert('Error retranslating segment');
    }
  };

  const handleOverride = async () => {
    if (!selectedSegment || !newTranslation) return;

    try {
      await axios.post(`/api/segments/${selectedSegment.id}/override`, {
        segment_id: selectedSegment.id,
        new_translation: newTranslation,
        engine: engine,
      });

      // Update segment
      setSegments((prev) =>
        prev.map((s) =>
          s.id === selectedSegment.id
            ? { ...s, translated_az: newTranslation, status: 'overridden' }
            : s
        )
      );

      setOverrideDialogOpen(false);
      setSelectedSegment(null);
      setNewTranslation('');
    } catch (error) {
      console.error('Error overriding:', error);
      alert('Error saving override');
    }
  };

  const openOverrideDialog = (segment) => {
    setSelectedSegment(segment);
    setNewTranslation(segment.translated_az || '');
    setOverrideDialogOpen(true);
  };

  return (
    <Box>
      <AppBar position="static">
        <Toolbar>
          <IconButton edge="start" color="inherit" onClick={() => navigate('/')}>
            <ArrowBack />
          </IconButton>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {book?.title_en || 'Book'}
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">
            {segments.filter(s => s.status === 'translated' || s.translated_az).length} / {segments.length} segments translated
          </Typography>
          {segments.some(s => s.status === 'pending' || !s.translated_az) && (
            <Button
              variant="contained"
              color="primary"
              onClick={handleTranslateAll}
            >
              Translate All Pending
            </Button>
          )}
        </Box>
        
        {segments.map((segment) => (
          <Paper key={segment.id} sx={{ p: 3, mb: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  English (Source)
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {segment.source_en}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Azerbaijani (Translation)
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {segment.translated_az || 'Not translated'}
                </Typography>
                
                {/* Segment Metrics */}
                {segment.translated_az && (
                  <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Translation Metrics
                    </Typography>
                    <Grid container spacing={1}>
                      {/* Translation Source Breakdown */}
                      <Grid item xs={12}>
                        <Box sx={{ mb: 1 }}>
                          <Typography variant="caption" color="text.secondary" display="block">
                            Translation Source:
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 0.5 }}>
                            {segment.from_style_memory ? (
                              <>
                                <Box sx={{ flex: 1, bgcolor: 'success.light', p: 0.5, borderRadius: 0.5, textAlign: 'center' }}>
                                  <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'success.dark' }}>
                                    Style Memory: 100%
                                  </Typography>
                                </Box>
                                <Box sx={{ flex: 0, bgcolor: 'primary.light', p: 0.5, borderRadius: 0.5, textAlign: 'center', minWidth: '80px' }}>
                                  <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'primary.dark' }}>
                                    Model: 0%
                                  </Typography>
                                </Box>
                              </>
                            ) : (
                              <>
                                <Box sx={{ flex: 0, bgcolor: 'success.light', p: 0.5, borderRadius: 0.5, textAlign: 'center', minWidth: '80px' }}>
                                  <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'success.dark' }}>
                                    Style: 0%
                                  </Typography>
                                </Box>
                                <Box sx={{ flex: 1, bgcolor: 'primary.light', p: 0.5, borderRadius: 0.5, textAlign: 'center' }}>
                                  <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'primary.dark' }}>
                                    AI Model: 100%
                                  </Typography>
                                </Box>
                              </>
                            )}
                          </Box>
                        </Box>
                      </Grid>
                      
                      {segment.style_similarity_score !== null && segment.style_similarity_score !== undefined && (
                        <Grid item xs={6}>
                          <Typography variant="caption" color="text.secondary">
                            Style Similarity:
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                            {(segment.style_similarity_score * 100).toFixed(1)}%
                          </Typography>
                        </Grid>
                      )}
                      
                      {segment.has_override && (
                        <Grid item xs={6}>
                          <Typography variant="caption" color="text.secondary">
                            Override Similarity:
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                            {segment.override_similarity_score !== null && segment.override_similarity_score !== undefined
                              ? (segment.override_similarity_score * 100).toFixed(1) + '%'
                              : 'N/A'}
                          </Typography>
                        </Grid>
                      )}
                    </Grid>
                  </Box>
                )}
              </Grid>
            </Grid>

            <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
              {!segment.translated_az && (
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => handleTranslate(segment.id, segment.source_en)}
                >
                  Translate
                </Button>
              )}
              <Button
                variant="outlined"
                size="small"
                startIcon={<Edit />}
                onClick={() => openOverrideDialog(segment)}
              >
                Edit/Override
              </Button>
            </Box>
          </Paper>
        ))}
      </Container>

      <Dialog open={overrideDialogOpen} onClose={() => setOverrideDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Override Translation</DialogTitle>
        <DialogContent>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Source (English):
          </Typography>
          <Typography variant="body2" sx={{ mb: 2, p: 1, bgcolor: 'grey.100' }}>
            {selectedSegment?.source_en}
          </Typography>

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Translation Engine</InputLabel>
            <Select value={engine} onChange={(e) => setEngine(e.target.value)}>
              <MenuItem value="gemini">Gemini</MenuItem>
              <MenuItem value="chatgpt">ChatGPT</MenuItem>
            </Select>
          </FormControl>

          <Button
            variant="outlined"
            onClick={() => handleRetranslate(selectedSegment?.id, selectedSegment?.source_en)}
            sx={{ mb: 2 }}
          >
            Retranslate with {engine}
          </Button>

          <TextField
            fullWidth
            multiline
            rows={6}
            label="New Translation"
            value={newTranslation}
            onChange={(e) => setNewTranslation(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOverrideDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleOverride} variant="contained" startIcon={<Check />}>
            Save Override
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default BookView;

