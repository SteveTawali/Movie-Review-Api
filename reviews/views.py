from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from .models import Movie, Review
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    MovieSerializer,
    ReviewSerializer,
)

# Custom Pagination
class ReviewPagination(PageNumberPagination):
    page_size = 10  # Adjust page size as needed
    page_size_query_param = 'page_size'
    max_page_size = 100  # Adjust max size if needed

# Review ViewSet for CRUD operations and sorting
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]  # Requires authentication for any review action
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['movie__title', 'rating']  # Search by movie title
    ordering_fields = ['created_at', 'rating']  # Allow sorting by rating or creation date
    pagination_class = ReviewPagination  # Add pagination to review list

    def get_queryset(self):
        queryset = Review.objects.all()
        movie_title = self.request.query_params.get('movie_title', None)
        rating = self.request.query_params.get('rating', None)

        if movie_title:
            queryset = queryset.filter(movie__title__icontains=movie_title)  # Filter by movie title

        if rating:
            try:
                rating = int(rating)
                if 1 <= rating <= 5:
                    queryset = queryset.filter(rating=rating)  # Filter by rating
                else:
                    return Response({"error": "Rating must be between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({"error": "Invalid rating value. Rating must be an integer between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)

        return queryset

    def list(self, request, *args, **kwargs):
        # Handle pagination
        queryset = self.get_queryset()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# Movie ViewSet for CRUD operations and search
class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    permission_classes = [IsAuthenticated]  # Requires authentication for any movie action
    filter_backends = [SearchFilter]
    search_fields = ['title', 'genre']  # Search by movie title and genre


# Registration view
class RegisterView(APIView):
    permission_classes = [AllowAny]  # Allows anyone to register (no authentication required)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()  # This will create the user using the serializer
            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# User Profile view
class UserProfileView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]  # Requires authentication to view profile

    def get_object(self):
        return self.request.user  # Return the currently authenticated user


# User List view (optional, if you need to view all users)
class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]  # Only admins can view all users

# User Update view
class UserUpdateView(APIView):
    permission_classes = [IsAuthenticated]  # Requires authentication to update profile

    def put(self, request):
        user = request.user
        data = request.data

        # Update user's information
        if 'email' in data:
            user.email = data['email']

        if 'password' in data:
            user.password = make_password(data['password'])  # Hash the new password

        if 'first_name' in data:
            user.first_name = data['first_name']

        if 'last_name' in data:
            user.last_name = data['last_name']

        user.save()

        return Response({"message": "User updated successfully"})


# User Delete view
class UserDeleteView(APIView):
    permission_classes = [IsAuthenticated]  # Requires authentication to delete profile

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"message": "User deleted successfully"}, status=status.HTTP_204_NO_CONTENT)



# Login view with JWT token generation
class LoginView(APIView):
    permission_classes = [AllowAny]  # Allows anyone to log in (no authentication required)

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)

        if user:
            refresh = RefreshToken.for_user(user)
            return Response(
                {"refresh": str(refresh), "access": str(refresh.access_token)}
            )

        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


# Movie management views (List, Detail, Create, Update, Delete)
class MovieListCreateView(APIView):
    permission_classes = [IsAdminUser]  # Only admin users can access this view

    def get(self, request):
        movies = Movie.objects.all()
        serializer = MovieSerializer(movies, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MovieSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MovieDetailView(APIView):
    permission_classes = [IsAdminUser]  # Only admin users can access this view

    def get(self, request, movie_id):
        movie = Movie.objects.get(id=movie_id)
        serializer = MovieSerializer(movie)
        return Response(serializer.data)

    def put(self, request, movie_id):
        movie = Movie.objects.get(id=movie_id)
        serializer = MovieSerializer(movie, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, movie_id):
        movie = Movie.objects.get(id=movie_id)
        movie.delete()
        return Response({"message": "Movie deleted successfully"})


# Review management with optional search by Movie Title and Rating filtering
class ReviewListCreateView(APIView):
    permission_classes = [IsAuthenticated]  # Requires authentication to interact with reviews

    def get(self, request, movie_id):
        reviews = Review.objects.filter(movie_id=movie_id)
        movie_title = request.query_params.get('movie_title', None)
        rating = request.query_params.get('rating', None)

        if movie_title:
            reviews = reviews.filter(movie__title__icontains=movie_title)  # Filter by movie title

        if rating:
            try:
                rating = int(rating)
                if 1 <= rating <= 5:
                    reviews = reviews.filter(rating=rating)  # Filter by rating
                else:
                    return Response({"error": "Rating must be between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({"error": "Invalid rating value. Rating must be an integer between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)

        # Apply pagination
        paginator = ReviewPagination()
        result_page = paginator.paginate_queryset(reviews, request)
        serializer = ReviewSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, movie_id):
        print("movie_id received:", movie_id)
        data = request.data
        data["movie"] = movie_id
        data["user"] = request.user.id
        serializer = ReviewSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Review Detail View (Edit/Delete Review)
class ReviewDetailView(APIView):
    permission_classes = [IsAuthenticated]  # Requires authentication to edit/delete reviews

    def put(self, request, review_id):
        review = Review.objects.get(id=review_id, user=request.user)
        serializer = ReviewSerializer(review, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, review_id):
        review = Review.objects.get(id=review_id, user=request.user)
        review.delete()
        return Response({"message": "Review deleted successfully"})


class CreateMovieReviewView(APIView):
    permission_classes = [IsAuthenticated]  # Requires authentication

    def post(self, request, movie_id):
        try:
            # Check if the movie exists
            movie = Movie.objects.get(id=movie_id)
        except Movie.DoesNotExist:
            return Response({"error": "Movie not found."}, status=status.HTTP_404_NOT_FOUND)

        # Initialize the serializer with request data
        serializer = ReviewSerializer(data=request.data)

        # Validate and save the review, passing the movie and user directly
        if serializer.is_valid():
            # Save the review with movie and user information
            serializer.save(movie=movie, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # If validation fails, return error response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)