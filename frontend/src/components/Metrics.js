import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  AppBar,
  Toolbar,
  IconButton,
  Button,
} from '@mui/material';
import { ArrowBack, Assessment, Refresh } from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import axios from 'axios';

function Metrics() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);

  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      const response = await axios.get('/api/metrics/summary');
      setMetrics(response.data);
    } catch (error) {
      console.error('Error fetching metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRetrain = async () => {
    if (!window.confirm('This will retrain the model with current override data. This may take a while. Continue?')) {
      return;
    }
    
    setRetraining(true);
    try {
      const response = await axios.post('/api/metrics/retrain');
      if (response.data.can_retrain) {
        alert('Retraining started! Check terminal for progress.');
      } else {
        alert(response.data.message);
      }
    } catch (error) {
      console.error('Error starting retraining:', error);
      alert('Error starting retraining: ' + (error.response?.data?.detail || error.message));
    } finally {
      setRetraining(false);
    }
  };

  const formatMetric = (value) => {
    if (value === null || value === undefined || isNaN(value)) {
      return 'N/A';
    }
    return typeof value === 'number' ? value.toFixed(2) : value;
  };

  const metricCards = [
    { title: 'BLEU Score', value: formatMetric(metrics?.bleu), color: '#1976d2' },
    { title: 'ChrF Score', value: formatMetric(metrics?.chrf), color: '#2e7d32' },
    { title: 'Style Similarity', value: formatMetric(metrics?.style_similarity_score), color: '#ed6c02' },
    { title: 'Override Rate', value: formatMetric(metrics?.manual_override_rate) + (metrics?.manual_override_rate !== null && metrics?.manual_override_rate !== undefined ? '%' : ''), color: '#d32f2f' },
    { title: 'Attribution Ratio', value: formatMetric(metrics?.attribution_ratio) + (metrics?.attribution_ratio !== null && metrics?.attribution_ratio !== undefined ? '%' : ''), color: '#9c27b0' },
  ];

  return (
    <Box>
      <AppBar position="static">
        <Toolbar>
          <IconButton edge="start" color="inherit" onClick={() => navigate('/')}>
            <ArrowBack />
          </IconButton>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Metrics Dashboard
          </Typography>
          <Button
            variant="contained"
            color="secondary"
            startIcon={<Refresh />}
            onClick={handleRetrain}
            disabled={retraining}
          >
            {retraining ? 'Retraining...' : 'Retrain Model'}
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Grid container spacing={3}>
          {metricCards.map((card, index) => (
            <Grid item xs={12} sm={6} md={4} key={index}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    {card.title}
                  </Typography>
                  <Typography variant="h4" sx={{ color: card.color }}>
                    {card.value}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        <Paper sx={{ p: 3, mt: 4 }}>
          <Typography variant="h6" gutterBottom>
            Translation Quality Metrics
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            These metrics help track the quality and style preservation of translations.
          </Typography>
          
          {/* Translation Source Statistics */}
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Translation Source Breakdown
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2, bgcolor: 'primary.light' }}>
                  <Typography variant="caption" color="text.secondary">
                    From AI Model
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 'bold', color: 'primary.dark' }}>
                    {metrics?.attribution_ratio !== null && metrics?.attribution_ratio !== undefined
                      ? (100 - metrics.attribution_ratio).toFixed(1) + '%'
                      : 'N/A'}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2, bgcolor: 'success.light' }}>
                  <Typography variant="caption" color="text.secondary">
                    From Style Memory
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 'bold', color: 'success.dark' }}>
                    {formatMetric(metrics?.attribution_ratio) + '%'}
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}

export default Metrics;

