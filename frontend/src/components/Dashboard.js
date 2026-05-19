import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Box,
  AppBar,
  Toolbar,
  IconButton,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import { Upload, Logout, Assessment } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';

function Dashboard() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [translationDirection, setTranslationDirection] = useState('en_to_az');
  const { logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchBooks();
  }, []);

  const fetchBooks = async () => {
    try {
      const response = await axios.get('/api/books');
      setBooks(response.data);
    } catch (error) {
      console.error('Error fetching books:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(
        `/api/books/upload?translation_direction=${translationDirection}`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      alert(response.data.message || 'Book uploaded successfully! Translation started.');
      fetchBooks();
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Error uploading file: ' + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <Box>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Translation AI System
          </Typography>
          <Button
            color="inherit"
            startIcon={<Assessment />}
            onClick={() => navigate('/metrics')}
          >
            Metrics
          </Button>
          <IconButton color="inherit" onClick={logout}>
            <Logout />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4">Books</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <ToggleButtonGroup
              value={translationDirection}
              exclusive
              onChange={(_, val) => { if (val) setTranslationDirection(val); }}
              size="small"
            >
              <ToggleButton value="en_to_az">EN → AZ</ToggleButton>
              <ToggleButton value="az_to_en">AZ → EN</ToggleButton>
            </ToggleButtonGroup>
            <Button
              variant="contained"
              component="label"
              startIcon={<Upload />}
            >
              Upload Book
              <input
                type="file"
                hidden
                accept=".pdf,.docx,.epub"
                onChange={handleFileUpload}
              />
            </Button>
          </Box>
        </Box>

        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Title</TableCell>
                <TableCell>Author</TableCell>
                <TableCell>Direction</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {books.map((book) => (
                <TableRow key={book.id}>
                  <TableCell>{book.id}</TableCell>
                  <TableCell>{book.title_en}</TableCell>
                  <TableCell>{book.author || '-'}</TableCell>
                  <TableCell>{book.translation_direction === 'az_to_en' ? 'AZ → EN' : 'EN → AZ'}</TableCell>
                  <TableCell>{book.status}</TableCell>
                  <TableCell>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => navigate(`/book/${book.id}`)}
                    >
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Container>
    </Box>
  );
}

export default Dashboard;

